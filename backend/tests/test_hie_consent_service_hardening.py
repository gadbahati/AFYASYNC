from pathlib import Path


SERVICE = Path(__file__).parents[1] / "app" / "hie" / "consent_service.py"


def test_consent_service_uses_real_patient_facility_enrollment_model():
    source = SERVICE.read_text()
    assert "from app.patients.models import PatientFacility" in source
    assert "PatientFacility.patient_id == patient_id" in source
    assert "PatientFacility.status == \"ACTIVE\"" in source


def test_consent_service_restricts_supported_purposes():
    source = SERVICE.read_text()
    assert '{"TREATMENT", "PAYMENT", "PUBLICHEALTH", "OPERATIONS"}' in source
    assert '"HIE_CONSENT_INVALID_PURPOSE"' in source
