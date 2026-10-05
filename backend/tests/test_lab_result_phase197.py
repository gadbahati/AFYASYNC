from uuid import uuid4

from app.hie.conformance import validate_bundle


def test_phase197_lab_result_bundle_is_conformant():
    pid = str(uuid4())
    oid = str(uuid4())
    obs = str(uuid4())
    report = str(uuid4())
    sr = str(uuid4())
    task = str(uuid4())
    prov = str(uuid4())

    bundle = {
        "resourceType": "Bundle",
        "id": str(uuid4()),
        "type": "collection",
        "entry": [
            {"fullUrl": f"urn:uuid:Patient/{pid}", "resource": {
                "resourceType": "Patient", "id": pid,
                "meta": {"profile": ["https://fhir.dha.go.ke/core/StructureDefinition/kenya-core-patient|1.0.0"]},
                "name": [{"text": "Example"}],
            }},
            {"fullUrl": f"urn:uuid:Organization/{oid}", "resource": {
                "resourceType": "Organization", "id": oid,
                "meta": {"profile": ["https://fhir.dha.go.ke/core/StructureDefinition/provider-organization|1.0.0"]},
                "identifier": [{"system": "https://afyasync.health.ke/fhir/facilities", "value": oid}],
            }},
            {"fullUrl": f"urn:uuid:ServiceRequest/{sr}", "resource": {
                "resourceType": "ServiceRequest", "id": sr,
                "meta": {"profile": ["https://fhir.dha.go.ke/core/StructureDefinition/kenya-core-servicerequest|1.0.0"]},
                "status": "completed", "intent": "order",
                "subject": {"reference": f"Patient/{pid}"},
                "code": {"coding": [{"system": "http://example.org/lab", "code": "LAB-1"}]},
                "authoredOn": "2026-10-05T10:00:00+00:00",
                "requester": {"reference": f"Organization/{oid}"},
            }},
            {"fullUrl": f"urn:uuid/Task/{task}", "resource": {
                "resourceType": "Task", "id": task,
                "meta": {"profile": ["https://fhir.dha.go.ke/core/StructureDefinition/kenya-core-task|1.0.0"]},
                "status": "completed", "intent": "order", "priority": "routine",
                "code": {"text": "Laboratory order fulfilment"},
                "description": "Laboratory test fulfilment",
                "focus": {"reference": f"ServiceRequest/{sr}"},
                "for": {"reference": f"Patient/{pid}"},
                "authoredOn": "2026-10-05T10:00:00+00:00",
            }},
            {"fullUrl": f"urn:uuid/Observation/{obs}", "resource": {
                "resourceType": "Observation", "id": obs,
                "meta": {"profile": ["https://fhir.dha.go.ke/core/StructureDefinition/kenya-core-observation|1.0.0"]},
                "status": "final",
                "category": [{"text": "Laboratory"}],
                "code": {"coding": [{"system": "http://example.org/lab", "code": "LAB-1"}]},
                "subject": {"reference": f"Patient/{pid}"},
                "effectiveDateTime": "2026-10-05T10:00:00+00:00",
            }},
            {"fullUrl": f"urn:uuid/DiagnosticReport/{report}", "resource": {
                "resourceType": "DiagnosticReport", "id": report,
                "meta": {"profile": ["https://fhir.dha.go.ke/core/StructureDefinition/kenya-core-diagnosticreport|1.0.0"]},
                "status": "final",
                "category": [{"text": "Laboratory"}],
                "code": {"text": "Laboratory result"},
                "subject": {"reference": f"Patient/{pid}"},
                "encounter": {"reference": "Encounter/example"},
                "effectiveDateTime": "2026-10-05T10:00:00+00:00",
                "issued": "2026-10-05T10:00:00+00:00",
                "performer": [{"reference": f"Organization/{oid}"}],
                "result": [{"reference": f"Observation/{obs}"}],
            }},
            {"fullUrl": f"urn:uuid/Provenance/{prov}", "resource": {
                "resourceType": "Provenance", "id": prov,
                "meta": {"profile": ["https://fhir.dha.go.ke/core/StructureDefinition/kenya-core-provenance|1.0.0"]},
                "target": [{"reference": f"Observation/{obs}"}, {"reference": f"DiagnosticReport/{report}"}],
                "recorded": "2026-10-05T10:00:00+00:00",
                "agent": [{"type": {"text": "verifier"}, "who": {"reference": f"Organization/{oid}"}}],
            }},
        ],
    }
    assert validate_bundle(bundle, require_provenance=True) == []
