from datetime import date, timedelta
from uuid import UUID

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.audit.service import record_audit
from app.facilities.models import Facility
from app.national_supply.schemas import NationalSupplyItem, NationalSupplyResponse
from app.pharmacy.models import InventoryBatch, InventoryItem, Medication


def get_national_supply(
    db: Session,
    *,
    actor_user_id: UUID,
    county: str | None = None,
    medication_code: str | None = None,
    low_stock_only: bool = False,
    limit: int = 100,
    offset: int = 0,
) -> NationalSupplyResponse:
    limit = min(max(limit, 1), 200)
    offset = min(max(offset, 0), 10000)
    today = date.today()
    expiry_cutoff = today + timedelta(days=30)
    county_value = county.strip() if county else None
    medication_value = medication_code.strip() if medication_code else None

    base = (
        select(InventoryItem.id)
        .join(Facility, Facility.id == InventoryItem.facility_id)
        .join(Medication, Medication.id == InventoryItem.medication_id)
        .where(
            Facility.status == "ACTIVE",
            InventoryItem.status == "ACTIVE",
            Medication.status == "ACTIVE",
        )
    )
    if county_value:
        base = base.where(Facility.county == county_value)
    if medication_value:
        base = base.where(Medication.code == medication_value)
    if low_stock_only:
        base = base.where(InventoryItem.current_quantity <= InventoryItem.minimum_quantity)

    total = int(db.scalar(select(func.count()).select_from(base.subquery())) or 0)
    rows = db.execute(
        select(
            InventoryItem,
            Facility,
            Medication,
            func.coalesce(func.sum(case((InventoryBatch.expiry_date >= today, InventoryBatch.quantity), else_=0)), 0).label("non_expired"),
            func.coalesce(func.sum(case((InventoryBatch.expiry_date.between(today, expiry_cutoff), InventoryBatch.quantity), else_=0)), 0).label("expiring"),
            func.min(case((InventoryBatch.expiry_date >= today, InventoryBatch.expiry_date), else_=None)).label("next_expiry"),
        )
        .join(Facility, Facility.id == InventoryItem.facility_id)
        .join(Medication, Medication.id == InventoryItem.medication_id)
        .outerjoin(InventoryBatch, InventoryBatch.inventory_item_id == InventoryItem.id)
        .where(InventoryItem.id.in_(base))
        .group_by(InventoryItem.id, Facility.id, Medication.id)
        .order_by(Facility.county.asc().nulls_last(), Facility.name.asc(), Medication.name.asc(), InventoryItem.id.asc())
        .offset(offset)
        .limit(limit)
    ).all()

    items = [
        NationalSupplyItem(
            facility_id=facility.id,
            facility_code=facility.facility_id,
            facility_name=facility.name,
            county=facility.county,
            medication_id=medication.id,
            medication_code=medication.code,
            medication_name=medication.name,
            generic_name=medication.generic_name,
            current_quantity=float(inventory.current_quantity or 0),
            minimum_quantity=float(inventory.minimum_quantity or 0),
            low_stock=float(inventory.current_quantity or 0) <= float(inventory.minimum_quantity or 0),
            non_expired_batch_quantity=float(non_expired or 0),
            expiring_within_30_days_quantity=float(expiring or 0),
            next_expiry_date=next_expiry.isoformat() if next_expiry else None,
        )
        for inventory, facility, medication, non_expired, expiring, next_expiry in rows
    ]

    record_audit(
        db,
        action="VIEW_NATIONAL_SUPPLY",
        resource_type="NATIONAL_SUPPLY",
        result="SUCCESS",
        user_id=actor_user_id,
        metadata={
            "county_filter": county_value,
            "medication_code_filter": medication_value,
            "low_stock_only": low_stock_only,
            "limit": limit,
            "offset": offset,
            "returned": len(items),
        },
        commit=True,
    )
    return NationalSupplyResponse(items=items, total=total, limit=limit, offset=offset)
