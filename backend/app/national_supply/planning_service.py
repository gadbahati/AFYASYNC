from collections import defaultdict
from math import isfinite
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

MAX_INPUT_ROWS = 50_000
MAX_DONORS_PER_RECOMMENDATION = 10


def _non_negative_quantity(value: object) -> float | None:
    try:
        quantity = float(value or 0)
    except (TypeError, ValueError):
        return None
    if not isfinite(quantity) or quantity < 0:
        return None
    return quantity


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
        .order_by(
            Medication.code.asc(),
            Facility.county.asc().nulls_last(),
            Facility.name.asc(),
            InventoryItem.id.asc(),
        )
        .limit(MAX_INPUT_ROWS)
    )
    if county_value:
        stmt = stmt.where(Facility.county == county_value)
    if medication_value:
        stmt = stmt.where(Medication.code == medication_value)

    rows = db.execute(stmt).all()
    grouped: dict[UUID, list[tuple[InventoryItem, Facility, Medication]]] = defaultdict(list)
    invalid_inventory_rows = 0
    for inventory, facility, medication in rows:
        current = _non_negative_quantity(inventory.current_quantity)
        minimum = _non_negative_quantity(inventory.minimum_quantity)
        if current is None or minimum is None:
            invalid_inventory_rows += 1
            continue
        grouped[medication.id].append((inventory, facility, medication))

    recommendations: list[SupplyReplenishmentRecommendation] = []
    for medication_rows in grouped.values():
        donor_pool: list[dict[str, object]] = []
        shortages: list[tuple[InventoryItem, Facility, Medication, float]] = []

        for inventory, facility, medication in medication_rows:
            current = _non_negative_quantity(inventory.current_quantity)
            minimum = _non_negative_quantity(inventory.minimum_quantity)
            if current is None or minimum is None:
                continue
            if current < minimum:
                shortages.append((inventory, facility, medication, minimum - current))
            elif current > minimum:
                donor_pool.append(
                    {
                        "inventory": inventory,
                        "facility": facility,
                        "surplus": current - minimum,
                    }
                )

        shortages.sort(key=lambda value: (value[1].county or "", value[1].name, str(value[0].id)))
        donor_pool.sort(key=lambda value: (-float(value["surplus"]), str(value["facility"].id)))

        for inventory, facility, medication, shortage in shortages:
            remaining = shortage
            donor_views: list[SupplyDonor] = []

            for donor in donor_pool:
                donor_facility = donor["facility"]
                donor_surplus = float(donor["surplus"])
                if donor_facility.id == facility.id or donor_surplus <= 0 or remaining <= 0:
                    continue

                allocation = min(remaining, donor_surplus)
                if allocation <= 0 or not isfinite(allocation):
                    continue

                donor_views.append(
                    SupplyDonor(
                        facility_id=donor_facility.id,
                        facility_code=donor_facility.facility_id,
                        facility_name=donor_facility.name,
                        county=donor_facility.county,
                        available_surplus=allocation,
                    )
                )
                donor["surplus"] = donor_surplus - allocation
                remaining -= allocation

                if len(donor_views) >= MAX_DONORS_PER_RECOMMENDATION:
                    break

            suggested = shortage - remaining
            if suggested <= 0:
                continue

            recommendations.append(
                SupplyReplenishmentRecommendation(
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
                )
            )
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
            "input_rows": len(rows),
            "invalid_inventory_rows": invalid_inventory_rows,
            "returned": len(recommendations),
        },
        commit=True,
    )
    return SupplyPlanningResponse(
        recommendations=recommendations,
        total_recommendations=len(recommendations),
        input_rows_considered=len(rows),
        input_rows_truncated=len(rows) >= MAX_INPUT_ROWS,
    )
