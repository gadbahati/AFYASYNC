from pathlib import Path

FHIR = Path(__file__).parents[1] / "app" / "hie" / "medication_statement.py"
ROUTER = Path(__file__).parents[1] / "app" / "hie" / "router.py"

def test_phase200_requires_verified_medication_mapping():
    source = FHIR.read_text()
    assert 'source_system="AFYASYNC:MEDICATION"' in source
    assert '"MEDICATION_CODE_NOT_NATIONALLY_MAPPED:"' in source

def test_phase200_is_facility_and_prescriber_scoped():
    source = FHIR.read_text()
    assert 'encounter.facility_id != facility_id' in source
    assert 'prescriber.facility_id != facility_id' in source
    assert 'prescriber.status != "ACTIVE"' in source

def test_phase200_exports_provenance_and_audit():
    source = FHIR.read_text()
    assert '"resourceType": "Provenance"' in source
    assert '"HIE_MEDICATION_STATEMENT_EXPORT"' in source
    assert 'assert_valid_bundle(bundle)' in source

def test_phase200_route_requires_clinical_read_permission():
    source = ROUTER.read_text()
    marker = '@router.get("/prescriptions/{prescription_id}/medication-statements/fhir")'
    section = source[source.index(marker):source.index('@router.get("/consents/{consent_id}/fhir")', source.index(marker))]
    assert 'require_permission("clinical.record.read")' in section

def test_phase200_does_not_claim_unverified_kenya_medication_statement_profile():
    source = FHIR.read_text()
    assert "kenya-core-medicationstatement" not in source


def test_phase200_capability_statement_advertises_resource():
    service = Path(__file__).parents[1] / "app" / "hie" / "service.py"
    source = service.read_text()
    assert '"type": "MedicationStatement"' in source
    assert '"search-type"' in source
