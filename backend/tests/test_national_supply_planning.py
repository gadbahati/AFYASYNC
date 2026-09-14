from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.national_supply.planning_schemas import SupplyPlanningResponse, SupplyReplenishmentRecommendation


def test_supply_planning_rejects_negative_shortage():
    with pytest.raises(ValidationError):
        SupplyReplenishmentRecommendation(
            facility_id=uuid4(), facility_code="F1", facility_name="Facility", county=None,
            medication_id=uuid4(), medication_code="M1", medication_name="Medicine",
            current_quantity=0, minimum_quantity=10, shortage_quantity=-1,
            suggested_transfer_quantity=1, donors=[],
        )


def test_supply_planning_response_is_bounded():
    with pytest.raises(ValidationError):
        SupplyPlanningResponse(total_recommendations=201, recommendations=[])
