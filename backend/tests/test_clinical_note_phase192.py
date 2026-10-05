from uuid import uuid4

from app.hie.conformance import validate_bundle, validate_kenya_core_resource


def test_phase192_clinical_note_document_reference_structure():
    document_id = f"clinical-note-{uuid4()}"
    bundle = {
        "resourceType": "Bundle",
        "id": f"clinical-note-fhir-{uuid4()}",
        "type": "collection",
        "entry": [
            {"fullUrl": f"urn:uuid:DocumentReference/{document_id}", "resource": {
                "resourceType": "DocumentReference", "id": document_id,
                "status": "current", "docStatus": "final",
                "type": {"text": "PROGRESS"}, "subject": {"reference": "Patient/example"},
                "author": [{"reference": "Organization/example"}],
                "context": {"encounter": [{"reference": "Encounter/example"}]},
                "content": [{"attachment": {"contentType": "text/plain", "data": "VGVzdA=="}}],
            }},
            {"fullUrl": "urn:uuid:Patient/example", "resource": {
                "resourceType": "Patient", "id": "example",
                "meta": {"profile": ["https://fhir.dha.go.ke/core/StructureDefinition/kenya-core-patient|1.0.0"]},
                "name": [{"text": "Example"}],
            }},
            {"fullUrl": "urn:uuid:Provenance/example", "resource": {
                "resourceType": "Provenance", "id": "example",
                "meta": {"profile": ["https://fhir.dha.go.ke/core/StructureDefinition/kenya-core-provenance|1.0.0"]},
                "target": [{"reference": f"DocumentReference/{document_id}"}],
                "recorded": "2026-10-05T10:00:00+00:00",
                "agent": [{"type": {"text": "clinical note author"}}],
            }},
        ],
    }
    assert validate_bundle(bundle, require_provenance=True) == []


def test_phase192_does_not_claim_unverified_document_reference_profile():
    resource = {
        "resourceType": "DocumentReference",
        "id": "clinical-note-example",
        "meta": {"profile": ["https://fhir.dha.go.ke/core/StructureDefinition/not-verified"]},
        "status": "current",
        "subject": {"reference": "Patient/example"},
    }
    assert validate_kenya_core_resource(resource) == []
