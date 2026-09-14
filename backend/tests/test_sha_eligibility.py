from datetime import date

import pytest
from pydantic import ValidationError

from app.coverage.sha_eligibility_schemas import SHAEligibilityRequest, SHAEligibilityResponse
from app.coverage.sha_eligibility_service import _normalise_response, _parse_date
from app.integrations.adapters import AdapterResult


def test_sha_request_normalizes_membership_number():
    request = SHAEligibilityRequest(person_id="11111111-1111-1111-1111-111111111111", membership_number="  shif-001  ")
    assert request.membership_number == "SHIF-001"


def test_sha_request_forbids_extra_fields():
    with pytest.raises(ValidationError):
        SHAEligibilityRequest(
            person_id="11111111-1111-1111-1111-111111111111",
            membership_number="SHIF-001",
            national_id_number="12345678",
        )


def test_sha_response_rejects_missing_eligibility_flag():
    with pytest.raises(ValueError, match="INVALID_SHA_RESPONSE"):
        _normalise_response(AdapterResult(status="SUCCEEDED", response_data={}))


def test_sha_response_normalizes_membership():
    data = _normalise_response(AdapterResult(status="SUCCEEDED", response_data={"eligible": True, "membership_number": " shif-001 "}))
    assert data["membership_number"] == "SHIF-001"


def test_sha_transport_failure_is_not_reported_as_ineligible():
    with pytest.raises(ValueError, match="SHA_ELIGIBILITY_UNAVAILABLE"):
        _normalise_response(AdapterResult(status="RETRYING", response_code="TRANSPORT_ERROR"))


def test_sha_dates_are_strict_iso_dates():
    assert _parse_date("2026-01-02", "start_date") == date(2026, 1, 2)
    with pytest.raises(ValueError, match="INVALID_SHA_RESPONSE_END_DATE"):
        _parse_date("not-a-date", "end_date")


def test_sha_response_schema_is_bounded():
    with pytest.raises(ValidationError):
        SHAEligibilityResponse(
            coverage_id=None,
            person_id="11111111-1111-1111-1111-111111111111",
            payer_id="22222222-2222-2222-2222-222222222222",
            payer_plan_id=None,
            membership_number="SHIF-001",
            eligible=True,
            verification_status="VERIFIED",
            start_date=None,
            end_date=None,
            external_reference="x" * 151,
            checked_at="2026-01-01T00:00:00+00:00",
        )
