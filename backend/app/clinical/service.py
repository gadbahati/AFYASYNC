from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit.service import record_audit
from app.clinical.models import Consultation, Diagnosis, Vital
from app.encounters.models import Encounter
from app.rbac.models import Staff


def _open_encounter(db: Session, encounter_id: UUID) -> Encounter:
    encounter = db.get(Encounter, encounter_id)
    if encounter is None:
        raise ValueError("ENCOUNTER_NOT_FOUND")
    if encounter.status != "OPEN":
        raise ValueError("ENCOUNTER_CLOSED")
    return encounter


def _staff_at_facility(db: Session, staff_id: UUID, facility_id: UUID) -> Staff:
    staff = db.get(Staff, staff_id)
    if staff is None or staff.facility_id != facility_id or staff.status != "ACTIVE":
        raise ValueError("STAFF_NOT_FOUND")
    return staff


def _calculate_bmi(weight_kg: float | None, height_cm: float | None) -> float | None:
    if not weight_kg or not height_cm:
        return None
    height_m = height_cm / 100
    if height_m <= 0:
        return None
    return round(weight_kg / (height_m * height_m), 2)


def record_vitals(db: Session, encounter_id: UUID, staff_id: UUID, data: dict, *, actor_user_id: UUID | None = None) -> Vital:
    encounter = _open_encounter(db, encounter_id)
    _staff_at_facility(db, staff_id, encounter.facility_id)
    vital = Vital(
        encounter_id=encounter_id,
        recorded_by=staff_id,
        bmi=_calculate_bmi(data.get("weight_kg"), data.get("height_cm")),
        **data,
    )
    db.add(vital)
    db.flush()
    if actor_user_id:
        record_audit(
            db,
            action="CLINICAL_VITALS_RECORDED",
            resource_type="VITAL",
            resource_id=str(vital.id),
            result="SUCCESS",
            user_id=actor_user_id,
            facility_id=encounter.facility_id,
            patient_id=encounter.patient_id,
            commit=False,
        )
    db.commit()
    db.refresh(vital)
    return vital


def create_or_update_consultation(db: Session, encounter_id: UUID, doctor_id: UUID, data: dict, *, actor_user_id: UUID | None = None) -> Consultation:
    encounter = _open_encounter(db, encounter_id)
    _staff_at_facility(db, doctor_id, encounter.facility_id)
    consultation = db.scalar(select(Consultation).where(Consultation.encounter_id == encounter_id))
    action = "CLINICAL_CONSULTATION_CREATED"
    if consultation is None:
        consultation = Consultation(encounter_id=encounter_id, doctor_id=doctor_id, **data)
        db.add(consultation)
    else:
        action = "CLINICAL_CONSULTATION_UPDATED"
        consultation.doctor_id = doctor_id
        for key, value in data.items():
            setattr(consultation, key, value)
    db.flush()
    if actor_user_id:
        record_audit(
            db,
            action=action,
            resource_type="CONSULTATION",
            resource_id=str(consultation.id),
            result="SUCCESS",
            user_id=actor_user_id,
            facility_id=encounter.facility_id,
            patient_id=encounter.patient_id,
            commit=False,
        )
    db.commit()
    db.refresh(consultation)
    return consultation


def add_diagnosis(db: Session, encounter_id: UUID, staff_id: UUID, data: dict, *, actor_user_id: UUID | None = None) -> Diagnosis:
    encounter = _open_encounter(db, encounter_id)
    _staff_at_facility(db, staff_id, encounter.facility_id)
    diagnosis = Diagnosis(encounter_id=encounter_id, recorded_by=staff_id, **data)
    db.add(diagnosis)
    db.flush()
    if actor_user_id:
        record_audit(
            db,
            action="CLINICAL_DIAGNOSIS_RECORDED",
            resource_type="DIAGNOSIS",
            resource_id=str(diagnosis.id),
            result="SUCCESS",
            user_id=actor_user_id,
            facility_id=encounter.facility_id,
            patient_id=encounter.patient_id,
            commit=False,
        )
    db.commit()
    db.refresh(diagnosis)
    return diagnosis


def get_encounter_clinical_summary(
    db: Session,
    encounter_id: UUID,
    facility_id: UUID,
) -> dict:
    """Facility-scoped clinical timeline for a single encounter.

    Returns vitals, consultation, and diagnoses. Does not include other facilities.
    """
    encounter = db.get(Encounter, encounter_id)
    if encounter is None:
        raise ValueError("ENCOUNTER_NOT_FOUND")
    if encounter.facility_id != facility_id:
        raise ValueError("FACILITY_ACCESS_DENIED")

    vitals = list(
        db.scalars(
            select(Vital)
            .where(Vital.encounter_id == encounter_id)
            .order_by(Vital.recorded_at.asc(), Vital.id.asc())
        )
    )
    consultation = db.scalar(select(Consultation).where(Consultation.encounter_id == encounter_id))
    diagnoses = list(
        db.scalars(
            select(Diagnosis)
            .where(Diagnosis.encounter_id == encounter_id)
            .order_by(Diagnosis.created_at.asc(), Diagnosis.id.asc())
        )
    )
    return {
        "encounter": encounter,
        "vitals": vitals,
        "consultation": consultation,
        "diagnoses": diagnoses,
    }
