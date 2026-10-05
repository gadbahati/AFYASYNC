from uuid import uuid4
from app.hie.conformance import validate_bundle


def test_phase194_clinical_care_plan_bundle_is_conformant():
    pid = str(uuid4())
    bundle = {
        "resourceType": "Bundle",
        "id": f"clinical-care-plan-fhir-{pid}",
        "type": "collection",
        "entry": [
            {"fullUrl": f"urn:uuid:Patient/{pid}", "resource": {
                "resourceType": "Patient",
                "id": pid,
                "meta": {"profile": ["https://fhir.dha.go.ke/core/StructureDefinition/kenya-core-patient|1.0.0"]},
                "name": [{"text": "Example"}],
            }},
            {"fullUrl": "urn:uuid:Organization/f1", "resource": {
                "resourceType": "Organization",
                "id": "f1",
                "meta": {"profile": ["https://fhir.dha.go.ke/core/StructureDefinition/provider-organization|1.0.0"]},
                "identifier": [{"system": "https://example.invalid/facility", "value": "f1"}],
            }},
            {"fullUrl": f"urn:uuid:CarePlan/{pid}", "resource": {
                "resourceType": "CarePlan",
                "id": pid,
                "status": "active",
                "intent": "plan",
                "title": "Follow-up",
                "subject": {"reference": f"Patient/{pid}"},
            }},
            {"fullUrl": f"urn:uuid:Provenance/p-{pid}", "resource": {
                "resourceType": "Provenance",
                "id": f"p-{pid}",
                "meta": {"profile": ["https://fhir.dha.go.ke/core/StructureDefinition/kenya-core-provenance|1.0.0"]},
                "target": [{"reference": f"CarePlan/{pid}"}],
                "recorded": "2026-10-05T10:00:00+00:00",
                "agent": [{"type": {"text": "author"}, "who": {"reference": "Organization/f1"}}],
            }},
        ],
    }
    assert validate_bundle(bundle, require_provenance=True) == []
