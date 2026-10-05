from uuid import uuid4

from app.hie.conformance import validate_kenya_core_resource


def test_phase184_careteam_has_required_fhir_fields():
    resource = {
        "resourceType": "CareTeam",
        "id": f"care-team-{uuid4()}",
        "status": "active",
        "subject": {"reference": "Patient/example"},
        "participant": [
            {"entity": {"reference": "Organization/example"}},
        ],
    }

    assert resource["status"] in {"proposed", "active", "suspended", "inactive", "entered-in-error"}
    assert resource["subject"]["reference"].startswith("Patient/")
    assert resource["participant"][0]["entity"]["reference"].startswith("Organization/")
    assert validate_kenya_core_resource(resource) == []


def test_phase184_careteam_does_not_claim_unverified_kenya_profile():
    resource = {
        "resourceType": "CareTeam",
        "id": "care-team-example",
        "meta": {
            "profile": [
                "https://fhir.dha.go.ke/core/StructureDefinition/not-verified"
            ]
        },
        "status": "active",
        "subject": {"reference": "Patient/example"},
    }

    # No Kenya Core CareTeam profile is asserted unless it has been verified.
    assert validate_kenya_core_resource(resource) == []
