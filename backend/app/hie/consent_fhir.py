"""FHIR Consent projection for persisted AfyaSync HIE consent records."""

from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from app.audit.service import record_audit
from app.facilities.models import Facility
from app.hie.conformance import assert_valid_bundle
from app.hie.consent_models import HieConsent
from app.hie.models import HieNode
from app.hie.models import HieNode
from app.hie.service import _facility_organization_resource, _patient_resource
from app.patients.models import Person


class ConsentFhirError(ValueError):
    pass


def build_consent_bundle(db: Session, *, consent_id: UUID, facility_id: UUID, actor_user_id: UUID | None = None) -> dict:
    consent = db.get(HieConsent, consent_id)
    if consent is None or consent.facility_id != facility_id:
        raise ConsentFhirError("CONSENT_NOT_FOUND")

    person = db.get(Person, consent.patient_id)
    if person is None:
        raise ConsentFhirError("PATIENT_NOT_FOUND")
    facility = db.get(Facility, facility_id)
    if facility is None:
        raise ConsentFhirError("FACILITY_NOT_FOUND")

    patient = _patient_resource(db, person)
    organization = _facility_organization_resource(db, facility_id)

    status = "active" if consent.status == "ACTIVE" and consent.decision == "PERMIT" else "inactive"
    resource = {
        "resourceType": "Consent",
        "id": str(consent.id),
        "meta": {"profile": ["https://fhir.dha.go.ke/core/StructureDefinition/kenya-core-consent|1.0.0"]},
        "status": status,
        "scope": {"text": consent.scope or "HIE information sharing"},
        "category": [{"text": "Health information sharing consent"}],
        "patient": {"reference": f"Patient/{person.id}"},
        "dateTime": (consent.created_at or datetime.now(timezone.utc)).isoformat(),
        "provision": {
            "type": "permit" if consent.decision == "PERMIT" else "deny",
            "purpose": [{"text": consent.purpose}],
        },
    }
    if consent.period_start or consent.period_end:
        resource["provision"]["period"] = {
            key: value.isoformat()
            for key, value in (("start", consent.period_start), ("end", consent.period_end))
            if value
        }
    if consent.revoked_at:
        resource["provision"]["period"] = {
            **resource["provision"].get("period", {}),
            "end": consent.revoked_at.isoformat(),
        }
    if consent.recipient_node_id:
        node = db.get(HieNode, consent.recipient_node_id)
        if node is None or node.status != "ACTIVE":
            raise ConsentFhirError("CONSENT_RECIPIENT_NODE_NOT_FOUND")
        if node.facility_id is None:
            raise ConsentFhirError("CONSENT_RECIPIENT_FACILITY_NOT_BOUND")
        resource["provision"]["recipient"] = [{"reference": f"Organization/{node.facility_id}"}]

    provenance = {
        "resourceType": "Provenance",
        "id": str(uuid4()),
        "meta": {"profile": ["https://fhir.dha.go.ke/core/StructureDefinition/kenya-core-provenance|1.0.0"]},
        "target": [{"reference": f"Consent/{consent.id}"}],
        "recorded": datetime.now(timezone.utc).isoformat(),
        "agent": [{"who": {"reference": f"Organization/{facility_id}"}, "type": {"text": "AfyaSync"}}],
    }
    bundle = {
        "resourceType": "Bundle",
        "id": f"consent-{uuid4()}",
        "type": "collection",
        "entry": [
            {"fullUrl": f"urn:uuid:{patient['id']}", "resource": patient},
            {"fullUrl": f"urn:uuid:{organization['id']}", "resource": organization},
            {"fullUrl": f"urn:uuid:{resource['id']}", "resource": resource},
            {"fullUrl": f"urn:uuid:{provenance['id']}", "resource": provenance},
        ],
    }
    assert_valid_bundle(bundle)
    record_audit(
        db, action="HIE_CONSENT_FHIR_EXPORT", resource_type="HIE_CONSENT",
        resource_id=str(consent.id), result="SUCCESS", user_id=actor_user_id,
        facility_id=facility_id, patient_id=consent.patient_id,
        metadata={"status": status, "purpose": consent.purpose}, commit=False,
    )
    return bundle
