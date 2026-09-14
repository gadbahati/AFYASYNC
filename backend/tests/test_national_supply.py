from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.national_supply.schemas import NationalSupplyItem, NationalSupplyResponse


def test_national_supply_item_rejects_negative_quantities():
    with pytest.raises(ValidationError):
        NationalSupplyItem(
            facility_id=uuid4(), facility_code="FAC-1", facility_name="Facility", county="Kirinyaga",
            medication_id=uuid4(), medication_code="MED-1", medication_name="Medicine",
            current_quantity=-1, minimum_quantity=0, low_stock=True,
            non_expired_batch_quantity=0, expiring_within_30_days_quantity=0,
        )


def test_national_supply_response_bounds_pagination():
    with pytest.raises(ValidationError):
        NationalSupplyResponse(items=[], total=0, limit=0, offset=0)
    response = NationalSupplyResponse(items=[], total=0, limit=200, offset=10000)
    assert response.limit == 200
