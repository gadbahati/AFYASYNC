from datetime import datetime, timezone
from uuid import uuid4

from app.interoperability.clinical_schemas import FHIREncounterResource
from app.interoperability.schemas import FHIRCapabilityResponse


def test_fhir_capability_advertises_r4_json():
    capability = FHIRCapabilityResponse()
    assert capability.fhirVersion == "R4"
    assert capability.format == ["json"]


def test_fhir_encounter_uses_canonical_period_and_subject():
    patient_id = uuid4()
    start = datetime.now(timezone.utc)
    encounter = FHIREncounterResource(
        id=uuid4(),
        status="finished",
        **{"class": {"system": "http://terminology.hl7.org/CodeSystem/v3-ActCode", "code": "AMB"}},
        period_start=start,
        patient_id=patient_id,
    )
    payload = encounter.model_dump(by_alias=True)
    assert payload["resourceType"] == "Encounter"
    assert payload["class"]["code"] == "AMB"
    assert payload["period"]["start"] == start
    assert payload["period"]["end"] is None
    assert payload["subject"] == {"reference": f"Patient/{patient_id}"}
    assert "period_start" not in payload
