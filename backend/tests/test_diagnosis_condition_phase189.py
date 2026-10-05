from uuid import uuid4

from app.hie.conformance import validate_kenya_core_resource


def test_phase189_condition_has_required_fhir_fields():
    resource = {
        "resourceType": "Condition",
        "id": f"condition-{uuid4()}",
        "meta": {
            "profile": [
                "https://fhir.dha.go.ke/core/StructureDefinition/condition|1.0.0"
            ]
        },
        "code": {
            "coding": [{"system": "http://snomed.info/sct", "code": "123"}],
            "text": "Example condition",
        },
        "subject": {"reference": "Patient/example"},
        "encounter": {"reference": "Encounter/example"},
        "recordedDate": "2026-10-05T00:00:00+00:00",
    }

    assert validate_kenya_core_resource(resource) == []


def test_phase189_condition_rejects_unverified_kenya_profile():
    resource = {
        "resourceType": "Condition",
        "id": "condition-example",
        "meta": {
            "profile": [
                "https://fhir.dha.go.ke/core/StructureDefinition/not-verified"
            ]
        },
        "code": {"text": "Example condition"},
        "subject": {"reference": "Patient/example"},
    }

    errors = validate_kenya_core_resource(resource)
    assert "Condition_MISSING_KENYA_CORE_PROFILE" in errors
