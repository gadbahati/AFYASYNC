from app.hie.conformance import validate_kenya_core_resource

PROFILE = "https://fhir.dha.go.ke/core/StructureDefinition/kenya-core-communication|1.0.0"

def test_communication_requires_referral_traceability():
    resource = {
        "resourceType": "Communication", "id": "c1",
        "meta": {"profile": [PROFILE]},
        "identifier": [{"use": "official", "type": {"text": "Referral communication"}, "system": "https://afyasync.health.ke/fhir/referral-communications", "value": "r1"}],
        "subject": {"reference": "Patient/p1"},
        "recipient": [{"reference": "Organization/o2"}],
        "sender": {"reference": "Organization/o1"},
        "payload": [{"contentString": "Referral follow-up"}],
    }
    assert validate_kenya_core_resource(resource) == []

def test_communication_rejects_missing_recipient():
    resource = {
        "resourceType": "Communication", "id": "c1",
        "meta": {"profile": [PROFILE]},
        "identifier": [{"use": "official", "type": {"text": "Referral communication"}, "system": "https://afyasync.health.ke/fhir/referral-communications", "value": "r1"}],
        "subject": {"reference": "Patient/p1"},
        "sender": {"reference": "Organization/o1"},
        "payload": [{"contentString": "Referral follow-up"}],
    }
    assert "COMMUNICATION_RECIPIENT_REQUIRED" in validate_kenya_core_resource(resource)
