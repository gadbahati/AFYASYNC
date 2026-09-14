from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.national_supply.planning_schemas import SupplyPlanningResponse, SupplyReplenishmentRecommendation


def _recommendation(**overrides):
    values = {
        "facility_id": uuid4(),
        "facility_code": "F1",
        "facility_name": "Facility",
        "county": None,
        "medication_id": uuid4(),
        "medication_code": "M1",
        "medication_name": "Medicine",
        "current_quantity": 0,
        "minimum_quantity": 10,
        "shortage_quantity": 10,
        "suggested_transfer_quantity": 10,
        "donors": [],
    }
    values.update(overrides)
    return SupplyReplenishmentRecommendation(**values)


def test_supply_planning_rejects_negative_shortage():
    with pytest.raises(ValidationError):
        _recommendation(shortage_quantity=-1)


def test_supply_planning_rejects_transfer_above_shortage():
    with pytest.raises(ValidationError):
        _recommendation(suggested_transfer_quantity=11, donors=[])


def test_supply_planning_requires_donors_to_cover_transfer():
    with pytest.raises(ValidationError):
        _recommendation(suggested_transfer_quantity=5, donors=[])


def test_supply_planning_response_requires_matching_total():
    recommendation = _recommendation()
    with pytest.raises(ValidationError):
        SupplyPlanningResponse(
            recommendations=[recommendation],
            total_recommendations=0,
        )


def test_supply_planning_response_is_bounded():
    with pytest.raises(ValidationError):
        SupplyPlanningResponse(total_recommendations=201, recommendations=[])
