"""Phase 192: ClinicalNote -> FHIR DocumentReference interoperability."""
from __future__ import annotations

from datetime import timezone
from base64 import b64encode
from html import escape
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit.service import record_audit
from app.clinical.models import ClinicalNote
from app.encounters.models import Encounter
from app.hie.conformance import assert_valid_bundle
from app.hie.provider_identity import provider_identity_resources
from app.hie.service import _facility_organization_resource, _patient_resource
from app.patients.models import Person
from app.rbac.models import Staff, User


KENYA_CORE_PROVENANCE_PROFILE = "https://fhir.dha.go.ke/core/StructureDefinition/kenya-core-provenance|1.0.0"


class ClinicalNoteFhirError(ValueError):
    pass


def build_clinical_note_bundle(
    db: Session,
    *,
    note_id: UUID,
    facility_id: UUID,
    actor_user_id: UUID | None = None,
) -> dict:
    note = db.get(ClinicalNote, note_id)
    if note is None:
        raise ClinicalNoteFhirError("CLINICAL_NOTE_NOT_FOUND")

    encounter = db.get(Encounter, note.encounter_id)
    if encounter is None:
        raise ClinicalNoteFhirError("ENCOUNTER_NOT_FOUND")
    if encounter.facility_id != facility_id:
        raise ClinicalNoteFhirError("ACCESS_DENIED")

    person = db.get(Person, encounter.patient_id)
    if person is None:
        raise ClinicalNoteFhirError("PATIENT_NOT_FOUND")

    patient = _patient_resource(db, person)
    patient["meta"] = {"profile": ["https://fhir.dha.go.ke/core/StructureDefinition/kenya-core-patient|1.0.0"]}
    facility = _facility_organization_resource(db, facility_id)

    author_staff = None
    if note.author_id:
        author_user = db.get(User, note.author_id)
        if author_user and author_user.person_id:
            author_staff = db.scalar(select(Staff).where(
                Staff.person_id == author_user.person_id,
                Staff.facility_id == facility_id,
                Staff.status == "ACTIVE",
            ))
    providers = (
        provider_identity_resources(db, facility_id=facility_id, staff_id=author_staff.id)
        if author_staff
        else []
    )
    role = next((r for r in providers if r.get("resourceType") == "PractitionerRole"), None)
    author = {"reference": f"PractitionerRole/{role['id']}"} if role else {"reference": f"Organization/{facility_id}"}

    created = note.created_at.astimezone(timezone.utc).isoformat()
    document_id = f"clinical-note-{note.id}"
    note_type = escape(note.note_type)
    body = escape(note.content or "")

    document = {
        "resourceType": "DocumentReference",
        "id": document_id,
        "status": "current",
        "docStatus": "final" if note.status == "FINAL" else "preliminary",
        "type": {"text": note.note_type},
        "subject": {"reference": f"Patient/{person.id}"},
        "date": created,
        "author": [author],
        "custodian": {"reference": f"Organization/{facility_id}"},
        "context": {"encounter": [{"reference": f"Encounter/{encounter.id}"}]},
        "content": [{
            "attachment": {
                "contentType": "text/html",
                "title": note.note_type,
                "data": b64encode((note.content or "").encode("utf-8")).decode("ascii"),
            },
            "format": {"display": "Clinical note"},
        }],
        "description": f"AfyaSync clinical note: {note_type}",
    }

    provenance = {
        "resourceType": "Provenance",
        "id": f"clinical-note-provenance-{note.id}",
        "meta": {"profile": [KENYA_CORE_PROVENANCE_PROFILE]},
        "target": [{"reference": f"DocumentReference/{document_id}"}],
        "recorded": created,
        "agent": [{"type": {"text": "clinical note author"}, "who": author}],
        "reason": [{"text": "Clinical note interoperability"}],
    }

    resources = [document, patient, facility, *providers, provenance]
    bundle = {
        "resourceType": "Bundle",
        "id": f"clinical-note-fhir-{note.id}",
        "type": "collection",
        "entry": [{
            "fullUrl": f"urn:uuid:{r['resourceType']}/{r['id']}",
            "resource": r,
        } for r in resources],
    }

    try:
        assert_valid_bundle(bundle)
    except ValueError as exc:
        raise ClinicalNoteFhirError(str(exc)) from exc

    record_audit(
        db,
        action="HIE_CLINICAL_NOTE_EXPORT",
        resource_type="CLINICAL_NOTE",
        resource_id=str(note.id),
        result="SUCCESS",
        user_id=actor_user_id,
        facility_id=facility_id,
        patient_id=person.id,
        metadata={"document_status": "final" if note.status == "FINAL" else "preliminary", "note_type": note.note_type},
        commit=False,
    )
    return bundle
