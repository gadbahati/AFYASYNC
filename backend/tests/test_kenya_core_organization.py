from app.hie.conformance import validate_kenya_core_resource

def test_provider_organization_profile_is_required():
    resource = {
        "resourceType": "Organization",
        "id": "facility-1",
        "meta": {"profile": ["https://fhir.dha.go.ke/core/StructureDefinition/provider-organization|1.0.0"]},
        "identifier": [{"use": "official", "value": "FID-01-123456-7"}],
        "active": True,
        "type": [{"text": "provider"}],
        "name": "Example Facility",
    }
    assert validate_kenya_core_resource(resource) == []

def test_wrong_organization_profile_is_rejected():
    resource = {
        "resourceType": "Organization",
        "id": "facility-1",
        "meta": {"profile": ["https://fhir.dha.go.ke/core/StructureDefinition/KenyaCoreOrganization|1.0.0"]},
        "identifier": [{"use": "official", "value": "x"}],
        "active": True,
        "type": [{"text": "provider"}],
        "name": "Example Facility",
    }
    assert "ORGANIZATION_MISSING_KENYA_CORE_PROFILE" in validate_kenya_core_resource(resource)
