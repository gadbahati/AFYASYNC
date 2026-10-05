from pathlib import Path

SERVICE = Path(__file__).parents[1] / "app" / "hie" / "delivery_service.py"


def test_delivery_rechecks_consent_before_transmission():
    source = SERVICE.read_text()
    marker = 'if job.status == "DEAD": raise ValueError("HIE_DELIVERY_JOB_DEAD")'
    assert marker in source
    section = source[source.index(marker):source.index("    node = db.get(HieNode", source.index(marker))]
    assert 'HieConsent.status == "ACTIVE"' in section
    assert 'HieConsent.decision == "PERMIT"' in section
    assert 'HieConsent.scope == "HIE_SHARE"' in section
    assert 'HieConsent.purpose == purpose' in section
    assert 'HIE_CONSENT_EXPIRED' in section
    assert 'HIE_PATIENT_CONSENT_REQUIRED' in section
