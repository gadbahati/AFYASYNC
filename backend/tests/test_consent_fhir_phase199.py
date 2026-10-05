from pathlib import Path

FHIR = Path(__file__).parents[1] / "app" / "hie" / "consent_fhir.py"
ROUTER = Path(__file__).parents[1] / "app" / "hie" / "router.py"

def test_phase199_consent_projection_is_facility_scoped():
    source = FHIR.read_text()
    assert 'consent.facility_id != facility_id' in source
    assert '"CONSENT_NOT_FOUND"' in source

def test_phase199_consent_projection_preserves_revocation():
    source = FHIR.read_text()
    assert 'consent.status == "ACTIVE"' in source
    assert 'consent.revoked_at' in source
    assert '"inactive"' in source

def test_phase199_consent_projection_uses_verified_provenance():
    source = FHIR.read_text()
    assert "kenya-core-provenance|1.0.0" in source
    assert 'HIE_CONSENT_FHIR_EXPORT' in source

def test_phase199_consent_route_requires_patient_read_access():
    source = ROUTER.read_text()
    marker = '@router.get("/consents/{consent_id}/fhir")'
    section = source[source.index(marker):source.index('@router.get("/consents")', source.index(marker))]
    assert 'require_permission("patients.record.read")' in section


def test_phase199_does_not_claim_unverified_kenya_consent_profile():
    source = FHIR.read_text()
    assert "kenya-core-consent" not in source

def test_phase199_projects_consent_as_a_collection_with_patient_and_provenance():
    source = FHIR.read_text()
    assert '"resourceType": "Bundle"' in source
    assert '"type": "collection"' in source
    assert '"resourceType": "Consent"' in source
    assert '"resourceType": "Provenance"' in source
    assert 'assert_valid_bundle(bundle)' in source
