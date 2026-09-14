from datetime import date
from uuid import uuid4

from app.patients.national_identity_schemas import NationalIdentityResolution
from app.patients.national_identity_service import _audit_identifier


def test_national_identity_resolution_contains_only_minimum_identity_fields():
    result = NationalIdentityResolution(
        afya_id="AF-00000001",
        person_id=uuid4(),
        first_name="Jane",
        middle_name=None,
        last_name="Doe",
        date_of_birth=date(1990, 1, 1),
        sex="FEMALE",
        patient_status="ACTIVE",
        identity_status="ACTIVE",
    )
    assert result.afya_id == "AF-00000001"
    assert "active_facility_count" not in result.model_fields
    assert "phone" not in result.model_fields
    assert "national_id_number" not in result.model_fields
    assert "address" not in result.model_fields
    assert "emergency_contact_phone" not in result.model_fields
    assert "next_of_kin_phone" not in result.model_fields


def test_audit_identifier_is_deterministic_and_non_reversible():
    first = _audit_identifier("AF-00000001")
    second = _audit_identifier("AF-00000001")
    assert first == second
    assert len(first) == 64
    assert first != "AF-00000001"
