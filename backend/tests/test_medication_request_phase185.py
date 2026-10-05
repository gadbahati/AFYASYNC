from uuid import uuid4

from app.hie.conformance import validate_kenya_core_resource


def test_phase185_medication_request_has_required_fhir_fields():
    resource = {
        "resourceType": "MedicationRequest",
        "id": f"medication-request-{uuid4()}",
        "status": "active",
        "intent": "order",
        "medicationCodeableConcept": {
            "coding": [{
                "system": "https://example.invalid/verified-medication",
                "code": "verified-code",
                "display": "Verified medication",
            }]
        },
        "subject": {"reference": "Patient/example"},
        "encounter": {"reference": "Encounter/example"},
        "requester": {"reference": "Practitioner/example"},
    }

    assert resource["status"] in {
        "active", "on-hold", "cancelled", "completed",
        "entered-in-error", "stopped", "draft", "unknown",
    }
    assert resource["intent"] in {
        "proposal", "plan", "order", "original-order",
        "reflex-order", "filler-order", "instance-order", "option",
    }
    assert resource["subject"]["reference"].startswith("Patient/")
    assert resource["medicationCodeableConcept"]["coding"]
    assert validate_kenya_core_resource(resource) == []


def test_phase185_does_not_claim_unverified_kenya_medication_request_profile():
    resource = {
        "resourceType": "MedicationRequest",
        "id": "medication-request-example",
        "meta": {
            "profile": [
                "https://fhir.dha.go.ke/core/StructureDefinition/not-verified"
            ]
        },
        "status": "active",
        "intent": "order",
        "subject": {"reference": "Patient/example"},
    }

    # No Kenya Core MedicationRequest profile is asserted until verified.
    assert validate_kenya_core_resource(resource) == []
