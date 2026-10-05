from pathlib import Path

ROOT = Path(__file__).parents[1] / "app" / "hie"

def test_phase204_patient_summary_has_kps_composition():
    s = (ROOT / "service.py").read_text()
    assert "ke-kps-composition" in s
    assert 'resourceType": "Composition"' in s
    assert 'type": "document"' in s

def test_phase204_kps_composition_conformance_is_registered():
    s = (ROOT / "conformance.py").read_text()
    assert 'KPS_COMPOSITION_PROFILE = KPS_BASE + "ke-kps-composition"' in s
    assert '"Composition": KPS_COMPOSITION_PROFILE' in s
    assert "COMPOSITION_SECTION_REQUIRED" in s

def test_phase204_summary_retrieval_requires_composition_first():
    s = (ROOT / "patient_summary_retrieval.py").read_text()
    assert "HIE_SUMMARY_COMPOSITION_FIRST_REQUIRED" in s
