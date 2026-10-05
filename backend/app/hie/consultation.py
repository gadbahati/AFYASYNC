"""FHIR interoperability for AfyaSync consultations using verified Kenya Core resources."""
from __future__ import annotations
from datetime import timezone
from uuid import UUID
from html import escape
from sqlalchemy.orm import Session
from app.audit.service import record_audit
from app.clinical.models import Consultation
from app.encounters.models import Encounter
from app.hie.conformance import assert_valid_bundle
from app.hie.provider_identity import provider_identity_resources
from app.hie.service import _facility_organization_resource, _patient_resource
from app.patients.models import Person

PROVENANCE_PROFILE = "https://fhir.dha.go.ke/core/StructureDefinition/kenya-core-provenance|1.0.0"
PATIENT_PROFILE = "https://fhir.dha.go.ke/core/StructureDefinition/kenya-core-patient|1.0.0"
ENCOUNTER_PROFILE = "https://fhir.dha.go.ke/core/StructureDefinition/kenya-core-encounter|1.0.0"

class ConsultationFhirError(ValueError):
    pass

def _section(title: str, value: str | None) -> dict | None:
    if not value:
        return None
    return {"title": title, "text": {"status": "generated", "div": f"<div>{escape(value)}</div>"}}

def build_consultation_bundle(db: Session, *, consultation_id: UUID, facility_id: UUID, actor_user_id: UUID | None = None) -> dict:
    consultation = db.get(Consultation, consultation_id)
    if consultation is None:
        raise ConsultationFhirError("CONSULTATION_NOT_FOUND")
    encounter = db.get(Encounter, consultation.encounter_id)
    if encounter is None:
        raise ConsultationFhirError("ENCOUNTER_NOT_FOUND")
    if encounter.facility_id != facility_id:
        raise ConsultationFhirError("ACCESS_DENIED")
    person = db.get(Person, encounter.patient_id)
    if person is None:
        raise ConsultationFhirError("PATIENT_NOT_FOUND")
    patient = _patient_resource(db, person)
    patient["meta"] = {"profile": [PATIENT_PROFILE]}
    encounter_resource = {
        "resourceType": "Encounter", "id": str(encounter.id),
        "meta": {"profile": [ENCOUNTER_PROFILE]},
        "status": "finished" if encounter.status != "OPEN" else "in-progress",
        "class": {"code": "AMB", "display": "Ambulatory"},
        "subject": {"reference": f"Patient/{person.id}"},
    }
    facility = _facility_organization_resource(db, facility_id)
    try:
        providers = provider_identity_resources(db, facility_id=facility_id, staff_id=consultation.doctor_id)
    except ValueError as exc:
        raise ConsultationFhirError(str(exc)) from exc
    role = next((r for r in providers if r.get("resourceType") == "PractitionerRole"), None)
    author = {"reference": f"PractitionerRole/{role['id']}"} if role else {"reference": f"Organization/{facility_id}"}
    sections = [x for x in (
        _section("Chief complaint", consultation.chief_complaint),
        _section("History", consultation.history),
        _section("Examination", consultation.examination),
        _section("Assessment", consultation.assessment),
        _section("Clinical notes", consultation.clinical_notes),
        _section("Treatment plan", consultation.treatment_plan),
    ) if x]
    recorded_dt = consultation.updated_at or consultation.created_at
    if recorded_dt is None:
        raise ConsultationFhirError("CONSULTATION_TIMESTAMP_REQUIRED")
    recorded = recorded_dt.astimezone(timezone.utc).isoformat()
    composition = {
        "resourceType": "Composition", "id": str(consultation.id),
        "status": "final" if consultation.status == "FINAL" else "preliminary",
        "type": {"text": "Clinical consultation"},
        "subject": {"reference": f"Patient/{person.id}"},
        "encounter": {"reference": f"Encounter/{encounter.id}"},
        "date": recorded, "author": [author],
        "title": "AfyaSync Clinical Consultation", "section": sections,
    }
    provenance = {
        "resourceType": "Provenance", "id": f"consultation-provenance-{consultation.id}",
        "meta": {"profile": [PROVENANCE_PROFILE]},
        "target": [{"reference": f"Composition/{consultation.id}"}],
        "recorded": recorded, "agent": [{"type": {"text": "author"}, "who": author}],
        "reason": [{"text": "Clinical consultation interoperability"}],
    }
    resources = [patient, encounter_resource, facility, *providers, composition, provenance]
    bundle = {
        "resourceType": "Bundle", "id": f"consultation-fhir-{consultation.id}",
        "type": "document", "timestamp": recorded,
        "entry": [{"fullUrl": f"urn:uuid:{r['resourceType']}/{r['id']}", "resource": r} for r in resources],
    }
    try:
        assert_valid_bundle(bundle)
    except ValueError as exc:
        raise ConsultationFhirError(str(exc)) from exc
    record_audit(db, action="HIE_CONSULTATION_EXPORT", resource_type="CONSULTATION",
                 resource_id=str(consultation.id), result="SUCCESS", user_id=actor_user_id,
                 facility_id=facility_id, patient_id=person.id,
                 metadata={"status": consultation.status}, commit=False)
    return bundle
