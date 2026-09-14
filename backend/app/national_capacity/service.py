from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.appointments.models import Appointment, Queue, QueueEntry
from app.audit.service import record_audit
from app.facilities.models import Department, Facility
from app.national_capacity.schemas import NationalCapacityFacility, NationalCapacityResponse


def get_national_capacity(db: Session, *, actor_user_id: UUID, county: str | None = None) -> NationalCapacityResponse:
    county_value = county.strip() if county else None
    if county_value == "":
        county_value = None

    facility_conditions = [Facility.status == "ACTIVE"]
    if county_value:
        facility_conditions.append(Facility.county == county_value)

    active_facilities = int(db.scalar(select(func.count(Facility.id)).where(*facility_conditions)) or 0)
    active_departments = int(db.scalar(select(func.count(Department.id)).join(Facility, Facility.id == Department.facility_id).where(*facility_conditions, Department.status == "ACTIVE")) or 0)

    now = datetime.now(timezone.utc)
    horizon = now + timedelta(days=7)
    appointment_conditions = [*facility_conditions, Appointment.appointment_at >= now, Appointment.appointment_at <= horizon, Appointment.status.in_(["SCHEDULED", "CONFIRMED"])]
    scheduled_appointments = int(db.scalar(select(func.count(Appointment.id)).join(Facility, Facility.id == Appointment.facility_id).where(*appointment_conditions)) or 0)

    waiting_conditions = [*facility_conditions, Queue.status == "ACTIVE", QueueEntry.status == "WAITING"]
    waiting_queue_entries = int(db.scalar(select(func.count(QueueEntry.id)).join(Queue, Queue.id == QueueEntry.queue_id).join(Facility, Facility.id == Queue.facility_id).where(*waiting_conditions)) or 0)

    facilities = []
    facility_rows = db.execute(select(Facility.id, Facility.facility_id, Facility.name, Facility.county).where(*facility_conditions).order_by(Facility.name.asc(), Facility.id.asc())).all()
    for facility_id, facility_code, facility_name, facility_county in facility_rows:
        departments = int(db.scalar(select(func.count(Department.id)).where(Department.facility_id == facility_id, Department.status == "ACTIVE")) or 0)
        appointments = int(db.scalar(select(func.count(Appointment.id)).where(Appointment.facility_id == facility_id, Appointment.appointment_at >= now, Appointment.appointment_at <= horizon, Appointment.status.in_(["SCHEDULED", "CONFIRMED"]))) or 0)
        waiting = int(db.scalar(select(func.count(QueueEntry.id)).join(Queue, Queue.id == QueueEntry.queue_id).where(Queue.facility_id == facility_id, Queue.status == "ACTIVE", QueueEntry.status == "WAITING")) or 0)
        facilities.append(NationalCapacityFacility(facility_id=str(facility_id), facility_code=facility_code, facility_name=facility_name, county=facility_county, departments=departments, scheduled_appointments=appointments, waiting_queue_entries=waiting))

    record_audit(db, action="VIEW_NATIONAL_CAPACITY", resource_type="NATIONAL_CAPACITY", result="SUCCESS", user_id=actor_user_id, metadata={"county_filter": county_value, "facility_count": len(facilities), "appointment_horizon_days": 7}, commit=True)
    return NationalCapacityResponse(active_facilities=active_facilities, active_departments=active_departments, scheduled_appointments=scheduled_appointments, waiting_queue_entries=waiting_queue_entries, facilities=facilities)
