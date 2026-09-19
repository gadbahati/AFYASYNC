from app.interoperability.schemas import FHIRCapabilityResponse


def test_fhir_capability_declares_supported_contracts():
    capability = FHIRCapabilityResponse()
    assert capability.fhirVersion == "R4"
    assert "Patient" in capability.supported_resources
    assert "AllergyIntolerance" in capability.supported_resources
    assert capability.dhis2_api_version == "2.40"
    assert capability.identifier_systems == ["https://afasync.health.go.ke/identifier/afya-id"]
