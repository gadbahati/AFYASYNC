"""HIE service — FHIR-style patient summary and referral packages."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit.service import record_audit
from app.clinical.models import Allergy
from app.encounters.models import Encounter
from app.hie.models import HieExportLog
from app.patients.models import AfyaIdentity, PatientFacility, Person
from app.pharmacy.models import Prescription, PrescriptionItem, Medication


def _require_enrollment(db: Session, patient_id: UUID, facility_id: UUID) -> Person:
    enrolled = db.scalar(
        select(PatientFacility.id).where(
            PatientFacility.patient_id == patient_id,
            PatientFacility.facility_id == facility_id,
            PatientFacility.status == "ACTIVE",
        )
    )
    if enrolled is None:
        raise ValueError("PATIENT_NOT_IN_FACILITY")
    person = db.get(Person, patient_id)
    if person is None or person.status not in {"ACTIVE", "INACTIVE"}:
        raise ValueError("PATIENT_NOT_FOUND")
    return person


def _patient_resource(db: Session, person: Person) -> dict:
    identity = db.scalar(select(AfyaIdentity).where(AfyaIdentity.person_id == person.id))
    identifiers = []
    if identity and identity.status == "ACTIVE":
        identifiers.append(
            {
                "system": "https://afyasync.health.ke/identifier/afya-id",
                "value": identity.afya_id,
            }
        )
    if person.national_id:
        identifiers.append(
            {
                "system": "https://afyasync.health.ke/identifier/national-id",
                "value": person.national_id,
            }
        )
    sex = (person.sex or "unknown").strip().lower()
    gender = {"female": "female", "male": "male", "other": "other"}.get(sex, "unknown")
    return {
        "resourceType": "Patient",
        "id": str(person.id),
        "identifier": identifiers,
        "name": [
            {
                "use": "official",
                "family": person.last_name,
                "given": [x for x in [person.first_name, person.middle_name] if x],
            }
        ],
        "birthDate": person.date_of_birth.isoformat() if person.date_of_birth else None,
        "gender": gender,
        "active": person.status == "ACTIVE",
    }


def build_patient_summary_bundle(
    db: Session,
    *,
    patient_id: UUID,
    facility_id: UUID,
    actor_user_id: UUID | None = None,
    purpose: str | None = None,
    destination: str | None = None,
) -> dict:
    """Composition-style document bundle: Patient + allergies + encounters + meds."""
    person = _require_enrollment(db, patient_id, facility_id)
    entries: list[dict] = []

    patient = _patient_resource(db, person)
    entries.append({"fullUrl": f"urn:uuid:{person.id}", "resource": patient})

    allergies = list(
        db.scalars(
            select(Allergy).where(
                Allergy.patient_id == patient_id,
                Allergy.status == "ACTIVE",
            ).limit(50)
        )
    )
    for a in allergies:
        entries.append(
            {
                "fullUrl": f"urn:uuid:{a.id}",
                "resource": {
                    "resourceType": "AllergyIntolerance",
                    "id": str(a.id),
                    "clinicalStatus": {"coding": [{"code": "active"}]},
                    "code": {"text": a.allergen},
                    "patient": {"reference": f"Patient/{person.id}"},
                    "criticality": (a.severity or "unknown").lower(),
                    "reaction": [{"description": a.reaction}] if a.reaction else [],
                },
            }
        )

    encounters = list(
        db.scalars(
            select(Encounter)
            .where(Encounter.patient_id == patient_id)
            .order_by(Encounter.created_at.desc())
            .limit(20)
        )
    )
    for enc in encounters:
        entries.append(
            {
                "fullUrl": f"urn:uuid:{enc.id}",
                "resource": {
                    "resourceType": "Encounter",
                    "id": str(enc.id),
                    "status": (enc.status or "unknown").lower(),
                    "class": {"code": getattr(enc, "encounter_type", None) or "AMB"},
                    "subject": {"reference": f"Patient/{person.id}"},
                    "period": {
                        "start": enc.created_at.isoformat() if enc.created_at else None,
                    },
                    "serviceProvider": {"reference": f"Organization/{enc.facility_id}"},
                },
            }
        )

    rxs = list(
        db.scalars(
            select(Prescription)
            .where(
                Prescription.patient_id == patient_id,
                Prescription.status.in_(["ACTIVE", "DISPENSED", "PRESCRIBED"]),
            )
            .order_by(Prescription.created_at.desc())
            .limit(20)
        )
    )
    for rx in rxs:
        items = list(
            db.scalars(
                select(PrescriptionItem).where(PrescriptionItem.prescription_id == rx.id)
            )
        )
        med_texts = []
        for it in items:
            med = db.get(Medication, it.medication_id)
            med_texts.append(
                {
                    "medicationCodeableConcept": {"text": med.name if med else str(it.medication_id)},
                    "dosageInstruction": [{"text": f"{it.dose} {it.frequency} {it.duration}"}],
                }
            )
        entries.append(
            {
                "fullUrl": f"urn:uuid:{rx.id}",
                "resource": {
                    "resourceType": "MedicationRequest",
                    "id": str(rx.id),
                    "status": (rx.status or "unknown").lower(),
                    "intent": "order",
                    "subject": {"reference": f"Patient/{person.id}"},
                    "medication": med_texts[0]["medicationCodeableConcept"] if med_texts else {"text": "unknown"},
                    "dosageInstruction": med_texts[0]["dosageInstruction"] if med_texts else [],
                    "contained": med_texts[1:] if len(med_texts) > 1 else [],
                },
            }
        )

    bundle_id = str(uuid4())
    bundle = {
        "resourceType": "Bundle",
        "id": bundle_id,
        "type": "document",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "total": len(entries),
        "entry": entries,
        "meta": {
            "tag": [
                {"system": "https://afyasync.health.ke/hie", "code": "PATIENT_SUMMARY"},
                {"system": "https://afyasync.health.ke/developer", "code": "BAHATI_GAD_WANGWE"},
            ]
        },
    }

    log = HieExportLog(
        facility_id=facility_id,
        patient_id=patient_id,
        export_type="PATIENT_SUMMARY",
        resource_count=len(entries),
        actor_user_id=actor_user_id,
        purpose=(purpose or "care-coordination")[:200],
        destination=(destination or "")[:200] or None,
        status="SUCCESS",
    )
    db.add(log)
    db.flush()

    record_audit(
        db,
        action="HIE_PATIENT_SUMMARY_EXPORT",
        resource_type="PERSON",
        resource_id=str(patient_id),
        result="SUCCESS",
        user_id=actor_user_id,
        facility_id=facility_id,
        patient_id=patient_id,
        metadata={"bundle_id": bundle_id, "resources": len(entries), "destination": destination},
        commit=False,
    )
    return bundle


def build_referral_package(
    db: Session,
    *,
    patient_id: UUID,
    facility_id: UUID,
    encounter_id: UUID | None = None,
    clinical_summary: str | None = None,
    actor_user_id: UUID | None = None,
    destination: str | None = None,
) -> dict:
    """Slimmer package for inter-facility referral / transfer."""
    summary = build_patient_summary_bundle(
        db,
        patient_id=patient_id,
        facility_id=facility_id,
        actor_user_id=actor_user_id,
        purpose="referral",
        destination=destination,
    )
    # Override log type for last export
    last = db.scalar(
        select(HieExportLog)
        .where(
            HieExportLog.facility_id == facility_id,
            HieExportLog.patient_id == patient_id,
        )
        .order_by(HieExportLog.created_at.desc())
        .limit(1)
    )
    if last:
        last.export_type = "REFERRAL_PACKAGE"
        last.notes = (clinical_summary or "")[:2000] or None
        if encounter_id:
            last.notes = ((last.notes or "") + f" encounter={encounter_id}")[:2000]

    summary["meta"]["tag"] = [
        {"system": "https://afyasync.health.ke/hie", "code": "REFERRAL_PACKAGE"},
        {"system": "https://afyasync.health.ke/developer", "code": "BAHATI_GAD_WANGWE"},
    ]
    if clinical_summary:
        summary["entry"].insert(
            1,
            {
                "fullUrl": f"urn:uuid:{uuid4()}",
                "resource": {
                    "resourceType": "Composition",
                    "status": "final",
                    "type": {"text": "Referral note"},
                    "subject": {"reference": f"Patient/{patient_id}"},
                    "date": datetime.now(timezone.utc).isoformat(),
                    "title": "AfyaSync Referral Package",
                    "section": [{"title": "Clinical summary", "text": {"div": clinical_summary[:4000]}}],
                },
            },
        )
        summary["total"] = len(summary["entry"])
    return summary


def list_export_logs(db: Session, facility_id: UUID, *, limit: int = 50) -> list[HieExportLog]:
    limit = min(max(limit, 1), 200)
    return list(
        db.scalars(
            select(HieExportLog)
            .where(HieExportLog.facility_id == facility_id)
            .order_by(HieExportLog.created_at.desc())
            .limit(limit)
        )
    )
