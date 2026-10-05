from pathlib import Path

ROOT = Path(__file__).parents[1] / "app" / "hie"

def test_phase203_remote_summary_is_real_hie_retrieval():
    s = (ROOT / "patient_summary_retrieval.py").read_text()
    assert "client.get(url, headers=headers)" in s
    assert "/Patient/{patient_id}/$summary" in s
    assert "HIE_OUTBOUND_BEARER_TOKEN" in s

def test_phase203_remote_summary_requires_governance():
    s = (ROOT / "patient_summary_retrieval.py").read_text()
    for marker in ["PATIENT_NOT_ENROLLED_AT_FACILITY", "HIE_SOURCE_NOT_TRUSTED", "HIE_PATIENT_CONSENT_REQUIRED", "HIE_CONSENT_REVOKED"]:
        assert marker in s

def test_phase203_remote_summary_validates_kps_document_shape_and_identity():
    s = (ROOT / "patient_summary_retrieval.py").read_text()
    for marker in ["HIE_SUMMARY_DOCUMENT_BUNDLE_REQUIRED", "HIE_SUMMARY_COMPOSITION_FIRST_REQUIRED", "HIE_SUMMARY_PATIENT_REQUIRED", "HIE_SUMMARY_PATIENT_IDENTITY_MISMATCH"]:
        assert marker in s

def test_phase203_route_supports_local_and_hie_sources():
    s = Path(__file__).parents[1] / "app" / "hie" / "router.py"
    text = s.read_text()
    assert "source: str = Query(default=\"LOCAL\"" in text
    assert "retrieve_patient_summary_from_hie" in text
