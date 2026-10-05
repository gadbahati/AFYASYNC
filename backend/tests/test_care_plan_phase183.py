from uuid import uuid4

from app.hie.conformance import validate_kenya_core_resource


def test_phase183_careplan_has_required_fhir_fields():
    resource = {
        "resourceType": "CarePlan",
        "id": f"care-plan-{uuid4()}",
        "status": "active",
        "intent": "plan",
        "subject": {"reference": "Patient/example"},
        "encounter": {"reference": "Encounter/example"},
    }
    assert resource["status"] in {"active", "completed", "revoked"}
    assert resource["intent"] == "plan"
    assert resource["subject"]["reference"].startswith("Patient/")
    assert resource["encounter"]["reference"].startswith("Encounter/")
    assert validate_kenya_core_resource(resource) == []


def test_phase183_unknown_careplan_profile_is_not_claimed_as_kenya_core():
    resource = {
        "resourceType": "CarePlan",
        "id": "care-plan-example",
        "meta": {"profile": ["https://fhir.dha.go.ke/core/StructureDefinition/not-verified"]},
        "status": "active",
        "intent": "plan",
        "subject": {"reference": "Patient/example"},
    }
    # CarePlan is deliberately not added to KENYA_CORE_PROFILES until a
    # published Kenya Core CarePlan profile is verified. The interoperability
    # layer must not manufacture conformance claims.
    assert validate_kenya_core_resource(resource) == []
