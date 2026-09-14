from datetime import datetime, timezone
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.national_referrals.schemas import NationalReferralItem, NationalReferralResponse


def _item() -> NationalReferralItem:
    now = datetime.now(timezone.utc)
    return NationalReferralItem(
        id=uuid4(),
        referral_id="REF-0001",
        source_facility_id=uuid4(), source_facility_code="SRC-1", source_facility_name="Source", source_county="Kirinyaga",
        destination_facility_id=uuid4(), destination_facility_code="DST-1", destination_facility_name="Destination", destination_county="Nyeri",
        destination_department_id=None, destination_department_name=None,
        priority="URGENT", status="SENT", created_at=now, updated_at=now,
    )


def test_national_referral_item_excludes_patient_and_clinical_fields():
    item = _item()
    assert "patient_id" not in item.model_dump()
    assert "reason" not in item.model_dump()
    assert "clinical_summary" not in item.model_dump()
    assert "referred_by" not in item.model_dump()


def test_national_referral_response_bounds_pagination():
    with pytest.raises(ValidationError):
        NationalReferralResponse(items=[], total=0, limit=0, offset=0, status_counts=[], priority_counts=[])
    response = NationalReferralResponse(items=[_item()], total=1, limit=200, offset=10000, status_counts=[], priority_counts=[])
    assert response.total == 1
