from uuid import uuid4

from app.hie.conformance import validate_bundle, validate_kenya_core_resource


def test_phase191_discharge_document_structure():
    composition_id = f"discharge-summary-{uuid4()}"
    bundle = {
        "resourceType": "Bundle",
        "id": f"discharge-fhir-{uuid4()}",
        "type": "document",
        "entry": [
            {
                "fullUrl": f"urn:uuid:Composition/{composition_id}",
                "resource": {
                    "resourceType": "Composition",
                    "id": composition_id,
                    "status": "final",
                    "type": {"text": "Discharge summary"},
                    "subject": {"reference": "Patient/example"},
                    "encounter": {"reference": "Encounter/example"},
                    "date": "2026-10-05T10:00:00+00:00",
                    "author": [{"reference": "Organization/example"}],
                    "title": "AfyaSync Discharge Summary",
                },
            },
            {
                "fullUrl": "urn:uuid:Patient/example",
                "resource": {
                    "resourceType": "Patient",
                    "id": "example",
                    "meta": {
                        "profile": [
                            "https://fhir.dha.go.ke/core/StructureDefinition/kenya-core-patient|1.0.0"
                        ]
                    },
                    "name": [{"text": "Example"}],
                },
            },
            {
                "fullUrl": "urn:uuid:Provenance/example",
                "resource": {
                    "resourceType": "Provenance",
                    "id": "example",
                    "meta": {
                        "profile": [
                            "https://fhir.dha.go.ke/core/StructureDefinition/kenya-core-provenance|1.0.0"
                        ]
                    },
                    "target": [{"reference": f"Composition/{composition_id}"}],
                    "recorded": "2026-10-05T10:00:00+00:00",
                    "agent": [{"type": {"text": "discharge author"}}],
                },
            },
        ],
    }
    assert validate_bundle(bundle, require_provenance=True) == []


def test_phase191_composition_does_not_claim_unverified_kenya_profile():
    resource = {
        "resourceType": "Composition",
        "id": "discharge-summary-example",
        "meta": {
            "profile": [
                "https://fhir.dha.go.ke/core/StructureDefinition/not-verified"
            ]
        },
        "status": "final",
        "type": {"text": "Discharge summary"},
        "subject": {"reference": "Patient/example"},
    }
    assert validate_kenya_core_resource(resource) == []
