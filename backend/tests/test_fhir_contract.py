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


def test_inbound_fhir_patient_id_is_not_treated_as_local_identity():
    from unittest.mock import MagicMock
    from app.hie.service import validate_inbound_bundle

    db = MagicMock()
    node = type("Node", (), {"status": "ACTIVE", "trust_level": "HIGH", "code": "TRUSTED-A", "facility_id": uuid4()})()
    db.get.return_value = node
    row = None
    def capture_add(value):
        nonlocal row
        row = value
    db.add.side_effect = capture_add
    db.flush.side_effect = lambda: None

    remote_id = str(uuid4())
    bundle = {
        "resourceType": "Bundle",
        "type": "document",
        "id": "remote-bundle-1",
        "entry": [{
            "resource": {
                "resourceType": "Patient",
                "id": remote_id,
                "identifier": [{"system": "https://afyasync.health.ke/identifier/afya-id", "value": "AFYA-REMOTE-1"}],
                "name": [{"use": "official", "family": "Doe", "given": ["Jane"]}],
            }
        }],
    }
    result = validate_inbound_bundle(
        db,
        facility_id=uuid4(),
        payload=bundle,
        source_code="TRUSTED-A",
        source_node_id=uuid4(),
        actor_user_id=uuid4(),
    )

    assert result["validation_status"] == "ACCEPTED"
    assert result["patient_id"] is None
    assert row is not None
    assert row.patient_id is None
    assert row.payload == bundle
