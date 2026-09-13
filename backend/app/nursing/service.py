from uuid import UUID
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.audit.service import record_audit
from app.nursing.models import NursingHandover, NursingNote, NursingObservation
from app.patients.models import PatientFacility
from app.encounters.models import Encounter


def _patient_ok(db: Session, patient_id: UUID, facility_id: UUID) -> bool:
    return db.scalar(select(PatientFacility.id).where(PatientFacility.patient_id == patient_id, PatientFacility.facility_id == facility_id, PatientFacility.status == "ACTIVE")) is not None


def _encounter_ok(db: Session, patient_id: UUID, encounter_id: UUID | None, facility_id: UUID) -> bool:
    if encounter_id is None: return True
    return db.scalar(select(Encounter.id).where(Encounter.id == encounter_id, Encounter.patient_id == patient_id, Encounter.facility_id == facility_id, Encounter.status == "OPEN")) is not None


def create_observation(db: Session, payload, facility_id: UUID, actor_user_id: UUID):
    if not _patient_ok(db, payload.patient_id, facility_id): raise ValueError("PATIENT_NOT_IN_FACILITY")
    if not _encounter_ok(db, payload.patient_id, payload.encounter_id, facility_id): raise ValueError("ENCOUNTER_NOT_OPEN")
    if payload.pain_score is not None and not 0 <= payload.pain_score <= 10: raise ValueError("INVALID_PAIN_SCORE")
    if not any(getattr(payload, field) is not None for field in ("temperature","heart_rate","respiratory_rate","systolic_bp","diastolic_bp","oxygen_saturation","pain_score","notes")): raise ValueError("OBSERVATION_EMPTY")
    item = NursingObservation(recorded_by=actor_user_id, facility_id=facility_id, **payload.model_dump()); db.add(item)
    record_audit(db, action="NURSING_OBSERVATION_RECORDED", resource_type="NursingObservation", result="SUCCESS", user_id=actor_user_id, resource_id=str(item.id), facility_id=facility_id, patient_id=payload.patient_id, commit=False)
    db.commit(); db.refresh(item); return item


def create_note(db: Session, payload, facility_id: UUID, actor_user_id: UUID):
    if not _patient_ok(db, payload.patient_id, facility_id): raise ValueError("PATIENT_NOT_IN_FACILITY")
    if not _encounter_ok(db, payload.patient_id, payload.encounter_id, facility_id): raise ValueError("ENCOUNTER_NOT_OPEN")
    item = NursingNote(author_id=actor_user_id, facility_id=facility_id, **payload.model_dump()); db.add(item)
    record_audit(db, action="NURSING_NOTE_CREATED", resource_type="NursingNote", result="SUCCESS", user_id=actor_user_id, resource_id=str(item.id), facility_id=facility_id, patient_id=payload.patient_id, commit=False)
    db.commit(); db.refresh(item); return item


def create_handover(db: Session, payload, facility_id: UUID, actor_user_id: UUID):
    if not _patient_ok(db, payload.patient_id, facility_id): raise ValueError("PATIENT_NOT_IN_FACILITY")
    item = NursingHandover(handed_over_by=actor_user_id, facility_id=facility_id, **payload.model_dump()); db.add(item)
    record_audit(db, action="NURSING_HANDOVER_CREATED", resource_type="NursingHandover", result="SUCCESS", user_id=actor_user_id, resource_id=str(item.id), facility_id=facility_id, patient_id=payload.patient_id, commit=False)
    db.commit(); db.refresh(item); return item
