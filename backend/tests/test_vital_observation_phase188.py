from uuid import uuid4

from app.hie.conformance import validate_kenya_core_resource


def test_phase188_vital_observation_required_fields():
    resource = {
        "resourceType": "Observation",
        "id": str(uuid4()),
        "status": "final",
        "category": [{"coding": [{"code": "vital-signs"}]}],
        "code": {"coding": [{"system": "https://example.org/terminology", "code": "temperature"}]},
        "subject": {"reference": "Patient/example"},
        "encounter": {"reference": "Encounter/example"},
        "effectiveDateTime": "2026-01-01T10:00:00+00:00",
        "valueString": "36.8",
    }
    assert resource["status"] in {"registered", "preliminary", "final", "amended", "corrected", "cancelled", "entered-in-error", "unknown"}
    assert resource["category"][0]["coding"][0]["code"] == "vital-signs"
    assert resource["subject"]["reference"].startswith("Patient/")
    assert resource["encounter"]["reference"].startswith("Encounter/")
    assert validate_kenya_core_resource({
        **resource,
        "meta": {"profile": ["https://fhir.dha.go.ke/core/StructureDefinition/kenya-core-observation|1.0.0"]},
    }) == []


def test_phase188_does_not_claim_unverified_profile():
    resource = {
        "resourceType": "Observation",
        "id": "vital-example",
        "meta": {"profile": ["https://fhir.dha.go.ke/core/StructureDefinition/not-verified"]},
        "status": "final",
    }
    assert validate_kenya_core_resource(resource) == ["Observation_MISSING_KENYA_CORE_PROFILE"]
