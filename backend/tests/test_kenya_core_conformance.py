from app.hie.conformance import validate_kenya_core_resource

def test_kenya_core_observation_profile_requires_core_fields():
    resource = {
        "resourceType": "Observation",
        "id": "obs-1",
        "meta": {"profile": ["https://fhir.dha.go.ke/core/StructureDefinition/kenya-core-observation|1.0.0"]},
        "status": "final",
        "category": [{"coding": [{"code": "laboratory"}]}],
        "code": {"text": "Glucose"},
        "subject": {"reference": "Patient/p1"},
        "effectiveDateTime": "2026-10-05T06:00:00Z",
    }
    assert validate_kenya_core_resource(resource) == []

def test_kenya_core_condition_requires_code_and_subject():
    resource = {
        "resourceType": "Condition",
        "id": "c-1",
        "meta": {"profile": ["https://fhir.dha.go.ke/core/StructureDefinition/condition|1.0.0"]},
        "subject": {"reference": "Patient/p1"},
        "code": {"text": "Local diagnosis"},
    }
    assert validate_kenya_core_resource(resource) == []
