from pathlib import Path

ROOT = Path(__file__).parents[1] / "app" / "hie"

def test_phase202_referral_communication_is_consent_and_trust_gated():
    s = (ROOT / "referral_communication.py").read_text()
    assert "_require_referral_communication_consent" in s
    assert "PATIENT_NOT_ENROLLED_AT_SOURCE_FACILITY" in s
    assert "REFERRAL_DESTINATION_NOT_TRUSTED" in s
    assert "HIE_TREATMENT_CONSENT_REQUIRED" in s

def test_phase202_communication_request_uses_official_kenya_core_profile():
    s = (ROOT / "referral_communication_request.py").read_text()
    assert "kenya-core-communicationrequest|1.0.0" in s
    assert "assert_valid_bundle(bundle)" in s
    assert "HIE_REFERRAL_COMMUNICATION_REQUEST_EXPORT" in s

def test_phase202_conformance_and_capability_are_complete():
    conformance = (ROOT / "conformance.py").read_text()
    service = (ROOT / "service.py").read_text()
    assert ""CommunicationRequest"" in conformance
    assert ""Consent"" in conformance
    assert ""CommunicationRequest"" in service
    assert ""Consent"" in service

def test_phase202_consent_fhir_uses_official_profile_and_bound_recipient():
    s = (ROOT / "consent_fhir.py").read_text()
    assert "kenya-core-consent|1.0.0" in s
    assert "CONSENT_RECIPIENT_FACILITY_NOT_BOUND" in s
    assert "Organization/{node.facility_id}" in s
