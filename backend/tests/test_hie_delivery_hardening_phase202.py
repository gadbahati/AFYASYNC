from pathlib import Path
P=Path(__file__).parents[1]/"app"/"hie"/"delivery_service.py"

def test_hie_delivery_requires_active_facility_enrollment():
    s=P.read_text()
    assert "PatientFacility" in s
    assert 'PATIENT_NOT_ENROLLED_AT_FACILITY' in s

def test_hie_delivery_binds_payload_to_patient():
    s=P.read_text()
    assert "payload_patients" in s
    assert 'HIE_PAYLOAD_PATIENT_MISMATCH' in s

def test_hie_delivery_keeps_trust_and_consent_gates():
    s=P.read_text()
    assert 'HIE_DESTINATION_NOT_TRUSTED' in s
    assert 'HIE_PATIENT_CONSENT_REQUIRED' in s
    assert 'HIE_CONSENT_EXPIRED' in s
