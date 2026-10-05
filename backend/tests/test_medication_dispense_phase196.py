from uuid import uuid4

from app.hie.conformance import validate_bundle


def test_phase196_medication_dispense_bundle_is_conformant():
    pid = str(uuid4())
    oid = str(uuid4())
    did = str(uuid4())
    bundle = {
        "resourceType": "Bundle",
        "id": f"medication-dispense-{did}",
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
            {"fullUrl": f"urn:uuid:MedicationDispense/{did}", "resource": {
                "resourceType": "MedicationDispense", "id": did,
                "status": "completed",
                "medicationCodeableConcept": {"coding": [{"system": "http://example.org/med", "code": "M-1"}]},
                "subject": {"reference": f"Patient/{pid}"},
                "quantity": {"value": 10},
            }},
            {"fullUrl": f"urn:uuid:Provenance/{did}", "resource": {
                "resourceType": "Provenance", "id": did,
                "meta": {"profile": ["https://fhir.dha.go.ke/core/StructureDefinition/kenya-core-provenance|1.0.0"]},
                "target": [{"reference": f"MedicationDispense/{did}"}],
                "recorded": "2026-10-05T10:00:00+00:00",
                "agent": [{"type": {"text": "prescriber"}, "who": {"reference": f"Organization/{oid}"}}],
            }},
        ],
    }
    assert validate_bundle(bundle, require_provenance=True) == []
