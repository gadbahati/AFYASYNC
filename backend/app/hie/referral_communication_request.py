"""FHIR Kenya Core CommunicationRequest projection for referral coordination."""
from __future__ import annotations
from datetime import timezone
from uuid import UUID
from sqlalchemy.orm import Session
from app.audit.service import record_audit
from app.encounters.models import Encounter
from app.hie.conformance import assert_valid_bundle
from app.hie.provider_identity import actor_provider_identity_resources
from app.hie.referral_communication import ReferralCommunicationError, _require_referral_communication_consent
from app.hie.referral_task import _get_referral, _PRIORITY, HL7_SERVICE_TYPE_SYSTEM, REFERRAL_SERVICE_TYPE_CODE, REFERRAL_SERVICE_TYPE_DISPLAY
from app.hie.service import _facility_organization_resource, _patient_resource
from app.patients.models import Person

KENYA_CORE_COMMUNICATION_REQUEST_PROFILE = "https://fhir.dha.go.ke/core/StructureDefinition/kenya-core-communicationrequest|1.0.0"

class ReferralCommunicationRequestError(ValueError):
    pass

_STATUS = {
    "CREATED": "active", "SENT": "active", "ACCEPTED": "active",
    "IN_PROGRESS": "active", "COMPLETED": "completed",
    "DECLINED": "revoked", "CANCELLED": "revoked",
}

def build_referral_communication_request_bundle(db: Session, *, referral_id: UUID, facility_id: UUID, actor_user_id: UUID | None, message: str, medium: str = "in-person") -> dict:
    if not message or not message.strip():
        raise ReferralCommunicationRequestError("COMMUNICATION_MESSAGE_REQUIRED")
    try:
        referral = _get_referral(db, referral_id, facility_id)
        _require_referral_communication_consent(db, referral=referral, facility_id=facility_id)
    except ReferralCommunicationError as exc:
        raise ReferralCommunicationRequestError(str(exc)) from exc
    person = db.get(Person, referral.patient_id)
    encounter = db.get(Encounter, referral.encounter_id)
    if person is None:
        raise ReferralCommunicationRequestError("PATIENT_NOT_FOUND")
    if encounter is None or encounter.facility_id != referral.source_facility_id:
        raise ReferralCommunicationRequestError("ENCOUNTER_NOT_FOUND")
    source_org = _facility_organization_resource(db, referral.source_facility_id)
    destination_org = _facility_organization_resource(db, referral.destination_facility_id)
    patient = _patient_resource(db, person)
    patient["meta"] = {"profile": ["https://fhir.dha.go.ke/core/StructureDefinition/kenya-core-patient|1.0.0"]}
    providers = actor_provider_identity_resources(db, user_id=actor_user_id, facility_id=referral.source_facility_id)
    role = next((r for r in providers if r.get("resourceType") == "PractitionerRole"), None)
    requester = {"reference": f"PractitionerRole/{role['id']}"} if role else {"reference": f"Organization/{referral.source_facility_id}"}
    authored = (referral.created_at or __import__("datetime").datetime.now(__import__("datetime").timezone.utc)).astimezone(timezone.utc).isoformat()
    request = {
        "resourceType": "CommunicationRequest",
        "id": f"referral-communication-request-{referral.id}",
        "meta": {"profile": [KENYA_CORE_COMMUNICATION_REQUEST_PROFILE]},
        "identifier": [{"use": "official", "type": {"text": "AfyaSync referral communication request"}, "system": "https://afyasync.health.ke/fhir/referral-communication-requests", "value": f"{referral.referral_id}:{authored}"}],
        "status": _STATUS.get(referral.status, "active"),
        "category": [{"coding": [{"system": "http://terminology.hl7.org/CodeSystem/communication-category", "code": "notification", "display": "Notification"}], "text": "Referral coordination"}],
        "priority": _PRIORITY.get(referral.priority, "routine"),
        "subject": {"reference": f"Patient/{person.id}"},
        "encounter": {"reference": f"Encounter/{encounter.id}"},
        "payload": [{"contentString": message.strip()}],
        "authoredOn": authored,
        "requester": requester,
        "recipient": [{"reference": f"Organization/{referral.destination_facility_id}"}],
        "medium": [{"text": medium}],
        "reasonCode": [{"text": referral.reason}],
        "note": [{"text": "Referral coordination communication request"}],
        "text": {"status": "generated", "div": "<div xmlns=\"http://www.w3.org/1999/xhtml\">Referral coordination communication request</div>"},
    }
    provenance = {
        "resourceType": "Provenance",
        "id": f"referral-communication-request-provenance-{referral.id}",
        "meta": {"profile": ["https://fhir.dha.go.ke/core/StructureDefinition/kenya-core-provenance|1.0.0"]},
        "target": [{"reference": f"CommunicationRequest/{request['id']}"}],
        "recorded": authored,
        "agent": [{"type": {"text": "author"}, "who": requester}],
        "reason": [{"text": "Referral communication coordination"}],
    }
    bundle = {"resourceType": "Bundle", "id": f"referral-communication-request-fhir-{referral.id}", "type": "collection", "entry": [{"fullUrl": f"urn:uuid:{r['resourceType']}/{r['id']}", "resource": r} for r in [patient, source_org, destination_org, *providers, request, provenance]]}
    try:
        assert_valid_bundle(bundle)
    except ValueError as exc:
        raise ReferralCommunicationRequestError(str(exc)) from exc
    record_audit(db, action="HIE_REFERRAL_COMMUNICATION_REQUEST_EXPORT", resource_type="REFERRAL", resource_id=str(referral.id), result="SUCCESS", user_id=actor_user_id, facility_id=facility_id, patient_id=referral.patient_id, metadata={"destination_facility_id": str(referral.destination_facility_id), "medium": medium}, commit=False)
    return bundle
