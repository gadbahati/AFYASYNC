from pathlib import Path

SERVICE = Path(__file__).parents[1] / "app" / "hie" / "service.py"


def test_phase206_enforces_kps_patient_summary_document_profile():
    source = SERVICE.read_text()
    assert "KPS_PATIENT_SUMMARY_MUST_BE_DOCUMENT" in source
    assert "KPS_COMPOSITION_MUST_BE_FIRST" in source
    assert "KPS_COMPOSITION_PROFILE_REQUIRED" in source
    assert "KPS_COMPOSITION_FINAL_REQUIRED" in source
    assert "KPS_COMPOSITION_SECTIONS_REQUIRED" in source
