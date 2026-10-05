from pathlib import Path

SERVICE = Path(__file__).parents[1] / "app" / "hie" / "service.py"

def test_phase201_binds_inbound_patient_identity():
    source = SERVICE.read_text()
    assert '"INBOUND_PATIENT_IDENTITY_MISMATCH"' in source
    assert 'payload_patient_refs' in source

def test_phase201_keeps_inbound_facility_and_trust_boundaries():
    source = SERVICE.read_text()
    assert 'row.facility_id != facility_id' in source
    assert '"INBOUND_SOURCE_NOT_TRUSTED"' in source
    assert 'node.trust_level not in {"HIGH", "NATIONAL"}' in source

def test_phase201_keeps_idempotent_imports():
    source = SERVICE.read_text()
    assert 'HieImportedResource.source_node_id == row.source_node_id' in source
    assert 'HieImportedResource.remote_resource_id == remote_id' in source

def test_phase201_keeps_purpose_and_sensitive_consent_controls():
    source = SERVICE.read_text()
    assert 'purpose = _bundle_purpose_of_use(row.payload or {})' in source
    assert 'consent_allows_sensitive' in source
    assert 'sensitivity = "SENSITIVE"' in source


def test_phase206_enforces_kps_patient_summary_document_profile():
    source = SERVICE.read_text()
    assert 'KPS_PATIENT_SUMMARY_MUST_BE_DOCUMENT' in source
    assert 'KPS_COMPOSITION_PROFILE_REQUIRED' in source
    assert 'KPS_COMPOSITION_FINAL_REQUIRED' in source
    assert 'KPS_COMPOSITION_SECTIONS_REQUIRED' in source
