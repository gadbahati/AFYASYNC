from datetime import datetime, timezone
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.audit.service import record_audit
from app.patients.models import PatientFacility
from app.theatre.models import TheatreBooking, TheatreProcedure, TheatreRecord


def _patient_ok(db, patient_id, facility_id):
    return db.scalar(select(PatientFacility.id).where(PatientFacility.patient_id == patient_id, PatientFacility.facility_id == facility_id, PatientFacility.status == "ACTIVE")) is not None

def create_procedure(db: Session, facility_id: UUID, actor: UUID, payload):
    item = TheatreProcedure(facility_id=facility_id, **payload.model_dump()); db.add(item)
    record_audit(db, action="THEATRE_PROCEDURE_CREATED", resource_type="TheatreProcedure", result="SUCCESS", user_id=actor, resource_id=str(item.id), facility_id=facility_id, commit=False)
    db.commit(); db.refresh(item); return item

def book_procedure(db: Session, facility_id: UUID, actor: UUID, payload):
    if not _patient_ok(db, payload.patient_id, facility_id): raise ValueError("PATIENT_NOT_IN_FACILITY")
    procedure = db.scalar(select(TheatreProcedure).where(TheatreProcedure.id == payload.procedure_id, TheatreProcedure.facility_id == facility_id, TheatreProcedure.status == "ACTIVE"))
    if not procedure: raise ValueError("PROCEDURE_NOT_FOUND")
    item = TheatreBooking(facility_id=facility_id, **payload.model_dump()); db.add(item)
    record_audit(db, action="THEATRE_BOOKING_CREATED", resource_type="TheatreBooking", result="SUCCESS", user_id=actor, resource_id=str(item.id), facility_id=facility_id, patient_id=payload.patient_id, commit=False)
    db.commit(); db.refresh(item); return item

def complete_procedure(db: Session, facility_id: UUID, actor: UUID, booking_id: UUID, payload):
    booking = db.scalar(select(TheatreBooking).where(TheatreBooking.id == booking_id, TheatreBooking.facility_id == facility_id).with_for_update())
    if not booking: raise ValueError("BOOKING_NOT_FOUND")
    if booking.status not in ("SCHEDULED", "IN_PROGRESS"): raise ValueError("BOOKING_NOT_ACTIVE")
    record = TheatreRecord(booking_id=booking_id, recorded_by=actor, **payload.model_dump()); db.add(record)
    booking.status = "COMPLETED"
    record_audit(db, action="THEATRE_PROCEDURE_COMPLETED", resource_type="TheatreRecord", result="SUCCESS", user_id=actor, resource_id=str(record.id), facility_id=facility_id, patient_id=booking.patient_id, commit=False)
    db.commit(); db.refresh(record); return record
