from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.patients.national_record_locator_schemas import (
    NationalRecordFacility,
    NationalRecordLocatorRequest,
    NationalRecordLocatorResponse,
)


def test_locator_request_requires_a_meaningful_access_reason():
    with pytest.raises(ValidationError):
        NationalRecordLocatorRequest(afya_id="AF-00000001", access_reason="why")


def test_locator_request_forbids_unexpected_fields():
    with pytest.raises(ValidationError):
        NationalRecordLocatorRequest(
            afya_id="AF-00000001",
            access_reason="Continuity of care",
            national_id_number="12345678",
        )


def test_locator_response_exposes_only_routing_metadata():
    facility = NationalRecordFacility(
        facility_id=uuid4(),
        facility_code="FAC-001",
        facility_name="Example Health Centre",
        county="Kirinyaga",
        enrollment_status="ACTIVE",
    )
    response = NationalRecordLocatorResponse(
        afya_id="AF-00000001",
        person_id=uuid4(),
        record_status="ACTIVE",
        facilities=[facility],
    )
    assert response.facilities[0].facility_name == "Example Health Centre"
    assert "phone" not in response.model_fields
    assert "address" not in response.model_fields
    assert "clinical_records" not in response.model_fields
    assert "national_id_number" not in response.model_fields


def test_locator_facility_metadata_is_bounded():
    with pytest.raises(ValidationError):
        NationalRecordFacility(
            facility_id=uuid4(),
            facility_code="F" * 33,
            facility_name="Facility",
            county=None,
            enrollment_status="ACTIVE",
        )
