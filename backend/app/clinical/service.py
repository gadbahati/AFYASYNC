from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit.service import record_audit
from app.clinical.models import CarePlan, Consultation, Diagnosis, Vital
from app.encounters.models import Encounter
from app.laboratory.models import LabOrder
from app.patients.models import PatientFacility, Person
from app.pharmacy.models import Prescription
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
    vital = Vital(encounter_id=encounter_id, recorded_by=staff_id, bmi=_calculate_bmi(data.get("weight_kg"), data.get("height_cm")), **data)
    db.add(vital)
    db.flush()
    if actor_user_id:
        record_audit(db, action="CLINICAL_VITALS_RECORDED", resource_type="VITAL", resource_id=str(vital.id), result="SUCCESS", user_id=actor_user_id, facility_id=encounter.facility_id, patient_id=encounter.patient_id, commit=False)
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
        record_audit(db, action=action, resource_type="CONSULTATION", resource_id=str(consultation.id), result="SUCCESS", user_id=actor_user_id, facility_id=encounter.facility_id, patient_id=encounter.patient_id, commit=False)
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
        record_audit(db, action="CLINICAL_DIAGNOSIS_RECORDED", resource_type="DIAGNOSIS", resource_id=str(diagnosis.id), result="SUCCESS", user_id=actor_user_id, facility_id=encounter.facility_id, patient_id=encounter.patient_id, commit=False)
    db.commit()
    db.refresh(diagnosis)
    return diagnosis


def get_encounter_clinical_summary(db: Session, encounter_id: UUID, facility_id: UUID) -> dict:
    encounter = db.get(Encounter, encounter_id)
    if encounter is None:
        raise ValueError("ENCOUNTER_NOT_FOUND")
    if encounter.facility_id != facility_id:
        raise ValueError("FACILITY_ACCESS_DENIED")
    vitals = list(db.scalars(select(Vital).where(Vital.encounter_id == encounter_id).order_by(Vital.recorded_at.asc(), Vital.id.asc())))
    consultation = db.scalar(select(Consultation).where(Consultation.encounter_id == encounter_id))
    diagnoses = list(db.scalars(select(Diagnosis).where(Diagnosis.encounter_id == encounter_id).order_by(Diagnosis.created_at.asc(), Diagnosis.id.asc())))
    lab_orders = list(db.scalars(select(LabOrder).where(LabOrder.encounter_id == encounter_id).order_by(LabOrder.created_at.asc(), LabOrder.id.asc())))
    prescriptions = list(db.scalars(select(Prescription).where(Prescription.encounter_id == encounter_id).order_by(Prescription.created_at.asc(), Prescription.id.asc())))
    return {"encounter": encounter, "vitals": vitals, "consultation": consultation, "diagnoses": diagnoses, "lab_orders": lab_orders, "prescriptions": prescriptions}


def _active_patient_at_facility(db: Session, patient_id: UUID, facility_id: UUID) -> Person:
    patient = db.get(Person, patient_id)
    if patient is None:
        raise ValueError("PATIENT_NOT_FOUND")
    enrolled = db.scalar(select(PatientFacility).where(PatientFacility.patient_id == patient_id, PatientFacility.facility_id == facility_id, PatientFacility.status == "ACTIVE"))
    if enrolled is None:
        raise ValueError("PATIENT_NOT_IN_FACILITY")
    return patient


def _validate_care_plan_encounter(db: Session, encounter_id: UUID | None, patient_id: UUID, facility_id: UUID) -> None:
    if encounter_id is None:
        return
    encounter = db.get(Encounter, encounter_id)
    if encounter is None or encounter.patient_id != patient_id:
        raise ValueError("ENCOUNTER_NOT_FOUND")
    if encounter.facility_id != facility_id:
        raise ValueError("FACILITY_ACCESS_DENIED")


def create_care_plan(db: Session, patient_id: UUID, facility_id: UUID, user_id: UUID, data: dict) -> CarePlan:
    _active_patient_at_facility(db, patient_id, facility_id)
    _validate_care_plan_encounter(db, data.get("encounter_id"), patient_id, facility_id)
    plan = CarePlan(patient_id=patient_id, facility_id=facility_id, created_by=user_id, **data)
    db.add(plan)
    db.flush()
    record_audit(db, action="CREATE_CARE_PLAN", resource_type="CARE_PLAN", resource_id=str(plan.id), result="SUCCESS", user_id=user_id, facility_id=facility_id, patient_id=patient_id, metadata={"status": plan.status}, commit=False)
    db.commit()
    db.refresh(plan)
    return plan


def list_care_plans(db: Session, patient_id: UUID, facility_id: UUID, status: str | None = None) -> list[CarePlan]:
    _active_patient_at_facility(db, patient_id, facility_id)
    query = select(CarePlan).where(CarePlan.patient_id == patient_id, CarePlan.facility_id == facility_id)
    if status:
        query = query.where(CarePlan.status == status)
    return list(db.scalars(query.order_by(CarePlan.updated_at.desc(), CarePlan.created_at.desc())))


def update_care_plan(db: Session, plan: CarePlan, user_id: UUID, facility_id: UUID, changes: dict) -> CarePlan:
    if plan.facility_id != facility_id:
        raise ValueError("FACILITY_ACCESS_DENIED")
    if not changes:
        raise ValueError("NO_CHANGES")
    new_status = changes.get("status")
    if new_status is not None and new_status != plan.status:
        allowed = {"ACTIVE": {"ACTIVE", "COMPLETED", "CANCELLED"}, "COMPLETED": {"COMPLETED"}, "CANCELLED": {"CANCELLED"}}
        if new_status not in allowed.get(plan.status, set()):
            raise ValueError("INVALID_CARE_PLAN_TRANSITION")
        plan.status = new_status
        plan.completed_at = datetime.now(timezone.utc) if new_status == "COMPLETED" else None
    for key, value in changes.items():
        if key not in {"status", "encounter_id"} and value is not None:
            setattr(plan, key, value)
    if "encounter_id" in changes:
        _validate_care_plan_encounter(db, changes["encounter_id"], plan.patient_id, facility_id)
        plan.encounter_id = changes["encounter_id"]
    db.add(plan)
    db.flush()
    record_audit(db, action="UPDATE_CARE_PLAN", resource_type="CARE_PLAN", resource_id=str(plan.id), result="SUCCESS", user_id=user_id, facility_id=facility_id, patient_id=plan.patient_id, metadata={"status": plan.status, "changed_fields": sorted(changes.keys())}, commit=False)
    db.commit()
    db.refresh(plan)
    return plan
