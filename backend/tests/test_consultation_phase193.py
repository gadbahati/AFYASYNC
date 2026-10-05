from uuid import uuid4
from app.hie.conformance import validate_bundle

PATIENT_PROFILE = "https://fhir.dha.go.ke/core/StructureDefinition/kenya-core-patient|1.0.0"
ENCOUNTER_PROFILE = "https://fhir.dha.go.ke/core/StructureDefinition/kenya-core-encounter|1.0.0"
PROVENANCE_PROFILE = "https://fhir.dha.go.ke/core/StructureDefinition/kenya-core-provenance|1.0.0"

def test_phase193_consultation_document_is_conformant():
    cid = str(uuid4())
    bundle = {
        "resourceType": "Bundle", "id": f"consultation-fhir-{cid}",
        "type": "document", "timestamp": "2026-10-05T10:00:00+00:00",
        "entry": [
            {"fullUrl": f"urn:uuid:Composition/{cid}", "resource": {
                "resourceType": "Composition", "id": cid, "status": "final",
                "type": {"text": "Clinical consultation"},
                "subject": {"reference": "Patient/p1"},
                "encounter": {"reference": "Encounter/e1"},
                "date": "2026-10-05T10:00:00+00:00",
                "author": [{"reference": "Organization/f1"}],
                "title": "AfyaSync Clinical Consultation",
                "section": [{"title": "Assessment", "text": {"status": "generated", "div": "<div>Stable</div>"}}],
            }},
            {"fullUrl": "urn:uuid:Patient/p1", "resource": {
                "resourceType": "Patient", "id": "p1", "meta": {"profile": [PATIENT_PROFILE]},
                "name": [{"text": "Example"}],
            }},
            {"fullUrl": "urn:uuid:Encounter/e1", "resource": {
                "resourceType": "Encounter", "id": "e1", "meta": {"profile": [ENCOUNTER_PROFILE]},
                "status": "finished", "subject": {"reference": "Patient/p1"},
            }},
            {"fullUrl": "urn:uuid:Organization/f1", "resource": {"resourceType": "Organization", "id": "f1"}},
            {"fullUrl": "urn:uuid:Provenance/pv1", "resource": {
                "resourceType": "Provenance", "id": "pv1", "meta": {"profile": [PROVENANCE_PROFILE]},
                "target": [{"reference": f"Composition/{cid}"}],
                "recorded": "2026-10-05T10:00:00+00:00",
                "agent": [{"type": {"text": "author"}, "who": {"reference": "Organization/f1"}}],
            }},
        ],
    }
    assert validate_bundle(bundle, require_provenance=True) == []

def test_phase193_uses_no_unverified_composition_profile():
    from app.hie.conformance import validate_kenya_core_resource
    resource = {"resourceType": "Composition", "id": str(uuid4()), "status": "final",
                "type": {"text": "Clinical consultation"}, "subject": {"reference": "Patient/p1"}}
    assert validate_kenya_core_resource(resource) == []
