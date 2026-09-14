from datetime import date
from uuid import uuid4

from app.interoperability.schemas import FHIRPatientResource


def test_fhir_patient_resource_is_minimal_and_bounded():
    patient_id = uuid4()
    resource = FHIRPatientResource(
        id=patient_id,
        identifier=[{"system": "AfyaSync", "value": "AF-00000001"}],
        name=[{"use": "official", "family": "Doe", "given": ["Jane"]}],
        birthDate=date(1990, 1, 1),
        gender="FEMALE",
        active=True,
    )
    assert resource.resourceType == "Patient"
    assert resource.id == patient_id
    assert "national_id_number" not in resource.model_dump()
    assert "phone" not in resource.model_dump()
    assert "address" not in resource.model_dump()
    assert "clinical" not in resource.model_dump()


def test_capability_does_not_advertise_write_access():
    from app.interoperability.schemas import FHIRCapabilityResponse

    result = FHIRCapabilityResponse()
    assert result.patient_read is True
    assert result.clinical_write is False
