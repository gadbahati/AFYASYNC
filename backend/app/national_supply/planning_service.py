from collections import defaultdict
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit.service import record_audit
from app.facilities.models import Facility
from app.national_supply.planning_schemas import (
    SupplyDonor,
    SupplyPlanningResponse,
    SupplyReplenishmentRecommendation,
)
from app.pharmacy.models import InventoryItem, Medication


def get_supply_planning(
    db: Session,
    *,
    actor_user_id: UUID,
    county: str | None = None,
    medication_code: str | None = None,
    limit: int = 100,
) -> SupplyPlanningResponse:
    limit = min(max(limit, 1), 200)
    county_value = county.strip() if county else None
    medication_value = medication_code.strip() if medication_code else None

    stmt = (
        select(InventoryItem, Facility, Medication)
        .join(Facility, Facility.id == InventoryItem.facility_id)
        .join(Medication, Medication.id == InventoryItem.medication_id)
        .where(
            Facility.status == "ACTIVE",
            InventoryItem.status == "ACTIVE",
            Medication.status == "ACTIVE",
        )
        .order_by(Facility.county.asc().nulls_last(), Facility.name.asc(), Medication.code.asc())
    )
    if county_value:
        stmt = stmt.where(Facility.county == county_value)
    if medication_value:
        stmt = stmt.where(Medication.code == medication_value)

    rows = db.execute(stmt).all()
    grouped: dict[UUID, list[tuple[InventoryItem, Facility, Medication]]] = defaultdict(list)
    for inventory, facility, medication in rows:
        grouped[medication.id].append((inventory, facility, medication))

    recommendations: list[SupplyReplenishmentRecommendation] = []
    for medication_rows in grouped.values():
        donors = []
        shortages = []
        for inventory, facility, medication in medication_rows:
            current = max(float(inventory.current_quantity or 0), 0.0)
            minimum = max(float(inventory.minimum_quantity or 0), 0.0)
            if current < minimum:
                shortages.append((inventory, facility, medication, minimum - current))
            elif current > minimum:
                donors.append((inventory, facility, medication, current - minimum))

        donors.sort(key=lambda value: (-value[3], str(value[1].id)))
        for inventory, facility, medication, shortage in shortages:
            remaining = shortage
            donor_views = []
            for donor_inventory, donor_facility, _, surplus in donors:
                if donor_facility.id == facility.id or remaining <= 0:
                    continue
                allocation = min(remaining, surplus)
                if allocation <= 0:
                    continue
                donor_views.append(SupplyDonor(
                    facility_id=donor_facility.id,
                    facility_code=donor_facility.facility_id,
                    facility_name=donor_facility.name,
                    county=donor_facility.county,
                    available_surplus=allocation,
                ))
                remaining -= allocation
                if len(donor_views) == 10:
                    break
            suggested = shortage - remaining
            if suggested <= 0:
                continue
            recommendations.append(SupplyReplenishmentRecommendation(
                facility_id=facility.id,
                facility_code=facility.facility_id,
                facility_name=facility.name,
                county=facility.county,
                medication_id=medication.id,
                medication_code=medication.code,
                medication_name=medication.name,
                current_quantity=float(inventory.current_quantity or 0),
                minimum_quantity=float(inventory.minimum_quantity or 0),
                shortage_quantity=shortage,
                suggested_transfer_quantity=suggested,
                donors=donor_views,
            ))
            if len(recommendations) >= limit:
                break
        if len(recommendations) >= limit:
            break

    record_audit(
        db,
        action="VIEW_NATIONAL_SUPPLY_PLAN",
        resource_type="NATIONAL_SUPPLY_PLAN",
        result="SUCCESS",
        user_id=actor_user_id,
        metadata={
            "county_filter": county_value,
            "medication_code_filter": medication_value,
            "limit": limit,
            "returned": len(recommendations),
        },
        commit=True,
    )
    return SupplyPlanningResponse(
        recommendations=recommendations,
        total_recommendations=len(recommendations),
    )
