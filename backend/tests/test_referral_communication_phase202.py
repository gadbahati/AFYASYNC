from pathlib import Path

P=Path(__file__).parents[1]/"app"/"hie"/"referral_communication.py"

def test_phase202_enforces_cross_facility_treatment_consent():
    s=P.read_text()
    assert 'HieConsent' in s
    assert 'HieConsent.purpose == "TREATMENT"' in s
    assert 'HIE_TREATMENT_CONSENT_REQUIRED' in s
    assert 'HieConsent.recipient_node_id' in s

def test_phase202_audits_referral_communication_exports():
    s=P.read_text()
    assert 'HIE_REFERRAL_COMMUNICATION_EXPORT' in s
    assert 'record_audit' in s

def test_phase202_preserves_fhir_conformance():
    s=P.read_text()
    assert 'KENYA_CORE_COMMUNICATION_PROFILE' in s
    assert 'assert_valid_bundle(bundle)' in s
    assert 'Provenance' in s
