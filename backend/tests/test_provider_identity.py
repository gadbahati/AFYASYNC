from app.hie.conformance import validate_kenya_core_resource
from app.hie.provider_identity import (
    LOCATION_PROFILE,
    PRACTITIONER_PROFILE,
    PRACTITIONER_ROLE_PROFILE,
)


def test_practitioner_profile_conforms():
    resource = {
        "resourceType": "Practitioner",
        "id": "staff-1",
        "meta": {"profile": [PRACTITIONER_PROFILE]},
        "active": True,
        "name": [{"family": "Wangwe", "given": ["Gad"]}],
    }
    assert validate_kenya_core_resource(resource) == []


def test_practitioner_role_requires_links():
    resource = {
        "resourceType": "PractitionerRole",
        "id": "staff-1",
        "meta": {"profile": [PRACTITIONER_ROLE_PROFILE]},
    }
    errors = validate_kenya_core_resource(resource)
    assert "PRACTITIONER_ROLE_PRACTITIONER_REQUIRED" in errors
    assert "PRACTITIONER_ROLE_ORGANIZATION_REQUIRED" in errors
    assert "PRACTITIONER_ROLE_CODE_REQUIRED" in errors


def test_location_profile_conforms():
    resource = {
        "resourceType": "Location",
        "id": "department-1",
        "meta": {"profile": [LOCATION_PROFILE]},
        "status": "active",
        "name": "Outpatient",
        "managingOrganization": {"reference": "Organization/facility-1"},
    }
    assert validate_kenya_core_resource(resource) == []
