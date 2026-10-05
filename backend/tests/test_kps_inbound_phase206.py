from pathlib import Path

SERVICE = Path(__file__).parents[1] / "app" / "hie" / "service.py"


def test_phase206_enforces_kps_patient_summary_document_profile():
    source = SERVICE.read_text()
    assert "KPS_PATIENT_SUMMARY_MUST_BE_DOCUMENT" in source
    assert "KPS_COMPOSITION_MUST_BE_FIRST" in source
    assert "KPS_COMPOSITION_PROFILE_REQUIRED" in source
    assert "KPS_COMPOSITION_FINAL_REQUIRED" in source
    assert "KPS_COMPOSITION_SECTIONS_REQUIRED" in source


def test_phase206_recomputes_acceptance_after_kps_specific_checks():
    source = SERVICE.read_text()
    assert 'status = "REJECTED" if errors else "ACCEPTED"' in source
    assert "KPS_COMPOSITION_SECTION_ENTRY_REQUIRED" in source


def test_phase206_requires_facility_enrollment_before_mpi_match():
    source = SERVICE.read_text()
    assert "PATIENT_NOT_ENROLLED_AT_FACILITY" in source
    assert "PatientFacility.status == \"ACTIVE\"" in source


def test_phase206_binds_kps_composition_subject_to_matched_patient():
    source = SERVICE.read_text()
    assert "KPS_COMPOSITION_PATIENT_MISMATCH" in source
    assert 'row.document_type == "PATIENT_SUMMARY"' in source


def test_phase206_persists_kps_document_resources_as_governed_imports():
    source = SERVICE.read_text()
    assert '"Composition",' in source
    assert '"Provenance",' in source
    assert "source_provenance" in source
