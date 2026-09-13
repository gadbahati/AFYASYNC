from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit.service import record_audit
from app.emergency.models import EmergencyTriage, EmergencyVisit
from app.patients.models import PatientFacility


TRIAGE_LEVELS = {"RESUSCITATION", "EMERGENCY", "URGENT", "LESS_URGENT", "NON_URGENT"}
DISPOSITIONS = {"DISCHARGED", "ADMITTED", "REFERRED", "TRANSFERRED", "OBSERVATION", "DECEASED"}


def create_emergency_visit(db: Session, patient_id: UUID, facility_id: UUID, actor_user_id: UUID, *, arrival_mode=None, chief_complaint=None, triage_level="URGENT", notes=None):
    if triage_level not in TRIAGE_LEVELS:
        raise ValueError("INVALID_TRIAGE_LEVEL")
    enrolled = db.scalar(select(PatientFacility.id).where(PatientFacility.patient_id == patient_id, PatientFacility.facility_id == facility_id, PatientFacility.status == "ACTIVE"))
    if not enrolled:
        raise ValueError("PATIENT_NOT_IN_FACILITY")
    visit = EmergencyVisit(id=uuid4(), visit_number=f"ER-{datetime.now(timezone.utc):%Y%m%d}-{uuid4().hex[:8].upper()}", patient_id=patient_id, facility_id=facility_id, arrival_mode=arrival_mode, chief_complaint=chief_complaint, triage_level=triage_level, notes=notes)
    db.add(visit)
    record_audit(db, actor_user_id=actor_user_id, action="EMERGENCY_VISIT_CREATED", entity_type="EmergencyVisit", entity_id=visit.id, facility_id=facility_id)
    db.commit()
    db.refresh(visit)
    return visit


def record_triage(db: Session, visit_id: UUID, facility_id: UUID, actor_user_id: UUID, **values):
    visit = db.scalar(select(EmergencyVisit).where(EmergencyVisit.id == visit_id, EmergencyVisit.facility_id == facility_id).with_for_update())
    if not visit:
        raise ValueError("EMERGENCY_VISIT_NOT_FOUND")
    triage = db.scalar(select(EmergencyTriage).where(EmergencyTriage.visit_id == visit_id))
    if triage:
        for key, value in values.items():
            setattr(triage, key, value)
    else:
        triage = EmergencyTriage(visit_id=visit_id, recorded_by=actor_user_id, **values)
        db.add(triage)
    visit.status = "TRIAGED"
    visit.seen_at = datetime.now(timezone.utc)
    record_audit(db, actor_user_id=actor_user_id, action="EMERGENCY_TRIAGE_RECORDED", entity_type="EmergencyVisit", entity_id=visit.id, facility_id=facility_id)
    db.commit()
    db.refresh(triage)
    return triage


def update_disposition(db: Session, visit_id: UUID, facility_id: UUID, actor_user_id: UUID, disposition: str, notes=None):
    if disposition not in DISPOSITIONS:
        raise ValueError("INVALID_DISPOSITION")
    visit = db.scalar(select(EmergencyVisit).where(EmergencyVisit.id == visit_id, EmergencyVisit.facility_id == facility_id).with_for_update())
    if not visit:
        raise ValueError("EMERGENCY_VISIT_NOT_FOUND")
    visit.disposition = disposition
    visit.notes = notes or visit.notes
    visit.status = "CLOSED"
    visit.closed_at = datetime.now(timezone.utc)
    record_audit(db, actor_user_id=actor_user_id, action="EMERGENCY_DISPOSITION_RECORDED", entity_type="EmergencyVisit", entity_id=visit.id, facility_id=facility_id, metadata={"disposition": disposition})
    db.commit()
    db.refresh(visit)
    return visit
