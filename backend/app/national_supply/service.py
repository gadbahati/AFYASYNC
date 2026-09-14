from datetime import date, timedelta
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.audit.service import record_audit
from app.facilities.models import Facility
from app.pharmacy.models import InventoryBatch, InventoryItem, Medication
from app.rbac.models import User
from app.national_supply.schemas import NationalSupplyItem, NationalSupplyResponse


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
    offset = max(offset, 0)
    today = date.today()
    expiry_cutoff = today + timedelta(days=30)

    base = (
        select(InventoryItem.id)
        .join(Facility, Facility.id == InventoryItem.facility_id)
        .join(Medication, Medication.id == InventoryItem.medication_id)
        .where(Facility.status == "ACTIVE", InventoryItem.status == "ACTIVE", Medication.status == "ACTIVE")
    )
    if county and county.strip():
        base = base.where(Facility.county == county.strip())
    if medication_code and medication_code.strip():
        base = base.where(Medication.code == medication_code.strip())
    if low_stock_only:
        base = base.where(InventoryItem.current_quantity <= InventoryItem.minimum_quantity)

    total = int(db.scalar(select(func.count()).select_from(base.subquery())) or 0)
    rows = db.execute(
        select(InventoryItem, Facility, Medication)
        .join(Facility, Facility.id == InventoryItem.facility_id)
        .join(Medication, Medication.id == InventoryItem.medication_id)
        .where(InventoryItem.id.in_(base))
        .order_by(Facility.county.asc().nulls_last(), Facility.name.asc(), Medication.name.asc(), InventoryItem.id.asc())
        .offset(offset)
        .limit(limit)
    ).all()

    items: list[NationalSupplyItem] = []
    for inventory, facility, medication in rows:
        batch_totals = db.execute(
            select(
                func.coalesce(func.sum(InventoryBatch.quantity), 0),
                func.coalesce(func.sum(func.nullif(InventoryBatch.quantity, 0)), 0),
                func.min(InventoryBatch.expiry_date),
            ).where(
                InventoryBatch.inventory_item_id == inventory.id,
                InventoryBatch.quantity > 0,
                InventoryBatch.expiry_date >= today,
            )
        ).one()
        non_expired = float(batch_totals[0] or 0)
        expiring = float(
            db.scalar(
                select(func.coalesce(func.sum(InventoryBatch.quantity), 0)).where(
                    InventoryBatch.inventory_item_id == inventory.id,
                    InventoryBatch.quantity > 0,
                    InventoryBatch.expiry_date >= today,
                    InventoryBatch.expiry_date <= expiry_cutoff,
                )
            )
            or 0
        )
        next_expiry = batch_totals[2].isoformat() if batch_totals[2] else None
        items.append(
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
                non_expired_batch_quantity=non_expired,
                expiring_within_30_days_quantity=expiring,
                next_expiry_date=next_expiry,
            )
        )

    record_audit(
        db,
        action="VIEW_NATIONAL_SUPPLY",
        resource_type="NATIONAL_SUPPLY",
        result="SUCCESS",
        user_id=actor_user_id,
        metadata={
            "county_filter": county.strip() if county else None,
            "medication_code_filter": medication_code.strip() if medication_code else None,
            "low_stock_only": low_stock_only,
            "limit": limit,
            "offset": offset,
            "returned": len(items),
        },
        commit=True,
    )
    return NationalSupplyResponse(items=items, total=total, limit=limit, offset=offset)
