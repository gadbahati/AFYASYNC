from pathlib import Path

ROOT = Path(__file__).parents[1] / "app" / "hie"

def test_phase205_has_governed_patient_summary_delivery():
    s = (ROOT / "delivery_service.py").read_text()
    assert "queue_patient_summary_delivery" in s
    assert "KPS_SUMMARY_DOCUMENT_BUNDLE_REQUIRED" in s
    assert "KPS_SUMMARY_COMPOSITION_FIRST_REQUIRED" in s

def test_phase205_delivery_route_is_exposed():
    s = (ROOT / "router.py").read_text()
    assert "/patient-summary/{patient_id}/deliver" in s
    assert "queue_patient_summary_delivery" in s

def test_phase205_delivery_has_patient_consent_and_idempotency_controls():
    s = (ROOT / "delivery_service.py").read_text()
    assert "HIE_PATIENT_CONSENT_REQUIRED" in s
    assert "HieDeliveryJob.idempotency_key == key" in s
    assert "HIE_OUTBOUND_DELIVERED" in s
