from app.hie.conformance import validate_bundle

def _bundle(bundle_type="document", include_composition=True):
    entries = []
    if include_composition:
        entries.append({"fullUrl": "urn:uuid:composition", "resource": {"resourceType": "Composition", "id": "composition"}})
    entries.append({"fullUrl": "urn:uuid:patient", "resource": {"resourceType": "Patient", "id": "patient-1"}})
    return {"resourceType": "Bundle", "id": "bundle-1", "type": bundle_type, "entry": entries}

def test_document_bundle_requires_first_composition():
    assert "DOCUMENT_COMPOSITION_MUST_BE_FIRST" not in validate_bundle(_bundle())
    assert "DOCUMENT_COMPOSITION_MUST_BE_FIRST" in validate_bundle(_bundle(include_composition=False))

def test_bundle_requires_exactly_one_patient():
    bundle = _bundle()
    bundle["entry"].append({"fullUrl": "urn:uuid:p2", "resource": {"resourceType": "Patient", "id": "patient-2"}})
    assert "PATIENT_RESOURCE_COUNT_INVALID" in validate_bundle(bundle)

def test_bundle_requires_resource_ids_and_full_urls():
    bundle = _bundle()
    bundle["entry"][1]["resource"].pop("id")
    bundle["entry"][1].pop("fullUrl")
    errors = validate_bundle(bundle)
    assert "MISSING_RESOURCE_ID_1" in errors
    assert "MISSING_FULL_URL_1" in errors
