"""FHIR Kenya Core Communication projection for referral follow-up."""
from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID
from sqlalchemy.orm import Session
from app.encounters.models import Encounter
from app.hie.conformance import assert_valid_bundle
from app.hie.provider_identity import actor_provider_identity_resources
from app.hie.referral_task import _get_referral, _PRIORITY, HL7_SERVICE_TYPE_SYSTEM, REFERRAL_SERVICE_TYPE_CODE
from app.hie.service import _facility_organization_resource, _patient_resource
from app.patients.models import Person

KENYA_CORE_COMMUNICATION_PROFILE = "https://fhir.dha.go.ke/core/StructureDefinition/kenya-core-communication|1.0.0"

class ReferralCommunicationError(ValueError):
    pass

def build_referral_communication_bundle(db: Session, *, referral_id: UUID, facility_id: UUID, actor_user_id: UUID | None, message: str, medium: str = "in-person", sent_at: datetime | None = None) -> dict:
    if not message or not message.strip():
        raise ReferralCommunicationError("COMMUNICATION_MESSAGE_REQUIRED")
    referral = _get_referral(db, referral_id, facility_id)
    person = db.get(Person, referral.patient_id)
    encounter = db.get(Encounter, referral.encounter_id)
    if person is None:
        raise ReferralCommunicationError("PATIENT_NOT_FOUND")
    if encounter is None or encounter.facility_id != referral.source_facility_id:
        raise ReferralCommunicationError("ENCOUNTER_NOT_FOUND")
    source_org = _facility_organization_resource(db, referral.source_facility_id)
    destination_org = _facility_organization_resource(db, referral.destination_facility_id)
    patient = _patient_resource(db, person)
    patient["meta"] = {"profile": ["https://fhir.dha.go.ke/core/StructureDefinition/kenya-core-patient|1.0.0"]}
    provider_resources = actor_provider_identity_resources(db, user_id=actor_user_id, facility_id=referral.source_facility_id)
    practitioner_role = next((r for r in provider_resources if r.get("resourceType") == "PractitionerRole"), None)
    sender = {"reference": f"PractitionerRole/{practitioner_role['id']}"} if practitioner_role else {"reference": f"Organization/{referral.source_facility_id}"}
    sent = (sent_at or datetime.now(timezone.utc)).astimezone(timezone.utc).isoformat()
    communication = {
        "resourceType": "Communication", "id": f"referral-communication-{referral.id}",
        "meta": {"profile": [KENYA_CORE_COMMUNICATION_PROFILE]},
        "identifier": [{"use": "official", "type": {"text": "AfyaSync referral communication"}, "system": "https://afyasync.health.ke/fhir/referral-communications", "value": f"{referral.referral_id}:{sent}"}],
        "status": "completed",
        "category": [{"coding": [{"system": HL7_SERVICE_TYPE_SYSTEM, "code": REFERRAL_SERVICE_TYPE_CODE, "display": "Referral coordination"}], "text": "Referral coordination"}],
        "priority": _PRIORITY.get(referral.priority, "routine"),
        "subject": {"reference": f"Patient/{person.id}"},
        "encounter": {"reference": f"Encounter/{encounter.id}"},
        "sent": sent,
        "basedOn": [{"reference": f"ServiceRequest/referral-{referral.id}"}],
        "recipient": [{"reference": f"Organization/{referral.destination_facility_id}"}],
        "sender": sender,
        "payload": [{"contentString": message.strip()}],
        "medium": [{"text": medium}],
        "text": {"status": "generated", "div": "<div xmlns=\"http://www.w3.org/1999/xhtml\">Referral coordination communication</div>"},
    }
    provenance = {
        "resourceType": "Provenance", "id": f"referral-communication-provenance-{referral.id}",
        "meta": {"profile": ["https://fhir.dha.go.ke/core/StructureDefinition/kenya-core-provenance|1.0.0"]},
        "target": [{"reference": f"Communication/{communication['id']}"}],
        "recorded": sent, "agent": [{"type": {"text": "author"}, "who": sender}],
        "reason": [{"text": "Referral follow-up and care coordination"}],
    }
    resources = [patient, source_org, destination_org, *provider_resources, communication, provenance]
    bundle = {"resourceType": "Bundle", "id": f"referral-communication-fhir-{referral.id}", "type": "collection",
              "entry": [{"fullUrl": f"urn:uuid:{r['resourceType']}/{r['id']}", "resource": r} for r in resources]}
    try:
        assert_valid_bundle(bundle)
    except ValueError as exc:
        raise ReferralCommunicationError(str(exc)) from exc
    return bundle
