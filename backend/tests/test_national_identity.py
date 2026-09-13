from datetime import date
from uuid import uuid4

from app.patients.national_identity_schemas import NationalIdentityResolution


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
        active_facility_count=2,
        identity_status="ACTIVE",
    )
    assert result.afya_id == "AF-00000001"
    assert result.active_facility_count == 2
    assert "phone" not in result.model_fields
    assert "national_id_number" not in result.model_fields
    assert "address" not in result.model_fields


def test_national_identity_resolution_rejects_negative_facility_count():
    try:
        NationalIdentityResolution(
            afya_id="AF-00000001",
            person_id=uuid4(),
            first_name="Jane",
            last_name="Doe",
            patient_status="ACTIVE",
            active_facility_count=-1,
            identity_status="ACTIVE",
        )
    except Exception as exc:
        assert "active_facility_count" in str(exc)
    else:
        raise AssertionError("negative active facility count must be rejected")
