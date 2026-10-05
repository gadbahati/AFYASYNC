"""FHIR Kenya Core Communication projection for referral follow-up."""
from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.encounters.models import Encounter
from app.hie.conformance import assert_valid_bundle
from app.hie.provider_identity import actor_provider_identity_resources
from app.hie.referral_task import _get_referral, _PRIORITY, HL7_SERVICE_TYPE_SYSTEM, REFERRAL_SERVICE_TYPE_CODE
from app.hie.service import _facility_organization_resource, _patient_resource
from app.hie.consent_models import HieConsent
from app.audit.service import record_audit
from app.patients.models import Person, PatientFacility
from app.hie.models import HieNode

KENYA_CORE_COMMUNICATION_PROFILE = "https://fhir.dha.go.ke/core/StructureDefinition/kenya-core-communication|1.0.0"

class ReferralCommunicationError(ValueError):
    pass

def _require_referral_communication_consent(db: Session, *, referral, facility_id: UUID) -> None:
    enrollment = db.scalar(select(PatientFacility).where(
        PatientFacility.patient_id == referral.patient_id,
        PatientFacility.facility_id == referral.source_facility_id,
        PatientFacility.status == "ACTIVE",
    ))
    if enrollment is None:
        raise ReferralCommunicationError("PATIENT_NOT_ENROLLED_AT_SOURCE_FACILITY")
    if referral.source_facility_id == referral.destination_facility_id:
        return
    if referral.destination_node_id is not None:
        node = db.get(HieNode, referral.destination_node_id)
        if node is None or node.status != "ACTIVE":
            raise ReferralCommunicationError("REFERRAL_DESTINATION_NODE_NOT_FOUND")
        if node.trust_level not in {"HIGH", "NATIONAL"}:
            raise ReferralCommunicationError("REFERRAL_DESTINATION_NOT_TRUSTED")
        if node.facility_id != referral.destination_facility_id:
            raise ReferralCommunicationError("REFERRAL_DESTINATION_NODE_MISMATCH")
    q = select(HieConsent).where(
        HieConsent.patient_id == referral.patient_id,
        HieConsent.facility_id == referral.source_facility_id,
        HieConsent.status == "ACTIVE",
        HieConsent.decision == "PERMIT",
        HieConsent.purpose == "TREATMENT",
        HieConsent.scope == "HIE_SHARE",
    )
    if referral.destination_node_id is not None:
        q = q.where((HieConsent.recipient_node_id == referral.destination_node_id) | HieConsent.recipient_node_id.is_(None))
    now = datetime.now(timezone.utc)
    for consent in db.scalars(q.order_by(HieConsent.created_at.desc())):
        if consent.period_start and now < consent.period_start:
            continue
        if consent.period_end and now > consent.period_end:
            continue
        if consent.revoked_at and now >= consent.revoked_at:
            continue
        return
    raise ReferralCommunicationError("HIE_TREATMENT_CONSENT_REQUIRED")

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
    _require_referral_communication_consent(db, referral=referral, facility_id=facility_id)
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
    record_audit(db, action="HIE_REFERRAL_COMMUNICATION_EXPORT", resource_type="REFERRAL", resource_id=str(referral.id), result="SUCCESS", user_id=actor_user_id, facility_id=facility_id, patient_id=referral.patient_id, metadata={"destination_facility_id": str(referral.destination_facility_id), "medium": medium}, commit=False)
    bundle = {"resourceType": "Bundle", "id": f"referral-communication-fhir-{referral.id}", "type": "collection",
              "entry": [{"fullUrl": f"urn:uuid:{r['resourceType']}/{r['id']}", "resource": r} for r in resources]}
    try:
        assert_valid_bundle(bundle)
    except ValueError as exc:
        raise ReferralCommunicationError(str(exc)) from exc
    return bundle
