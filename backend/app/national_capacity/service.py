from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.appointments.models import Appointment, Queue, QueueEntry
from app.audit.service import record_audit
from app.facilities.models import Department, Facility
from app.national_capacity.schemas import NationalCapacityFacility, NationalCapacityResponse


_ACTIVE_APPOINTMENT_STATUSES = ("SCHEDULED", "CONFIRMED")


def get_national_capacity(db: Session, *, actor_user_id: UUID, county: str | None = None) -> NationalCapacityResponse:
    county_value = county.strip() if county else None
    if county_value == "":
        county_value = None
    facility_conditions = [Facility.status == "ACTIVE"]
    if county_value:
        facility_conditions.append(Facility.county == county_value)

    now = datetime.now(timezone.utc)
    horizon = now + timedelta(days=7)
    active_facilities = int(db.scalar(select(func.count(Facility.id)).where(*facility_conditions)) or 0)
    active_departments = int(db.scalar(select(func.count(Department.id)).join(Facility, Facility.id == Department.facility_id).where(*facility_conditions, Department.status == "ACTIVE")) or 0)
    scheduled_appointments = int(db.scalar(select(func.count(Appointment.id)).join(Facility, Facility.id == Appointment.facility_id).where(*facility_conditions, Appointment.appointment_at >= now, Appointment.appointment_at <= horizon, Appointment.status.in_(_ACTIVE_APPOINTMENT_STATUSES))) or 0)
    waiting_queue_entries = int(db.scalar(select(func.count(QueueEntry.id)).join(Queue, Queue.id == QueueEntry.queue_id).join(Facility, Facility.id == Queue.facility_id).where(*facility_conditions, Queue.status == "ACTIVE", QueueEntry.status == "WAITING")) or 0)

    facility_rows = db.execute(select(Facility.id, Facility.facility_id, Facility.name, Facility.county).where(*facility_conditions).order_by(Facility.name.asc(), Facility.id.asc())).all()
    facility_ids = [row[0] for row in facility_rows]
    department_counts = dict(db.execute(select(Department.facility_id, func.count(Department.id)).where(Department.facility_id.in_(facility_ids), Department.status == "ACTIVE").group_by(Department.facility_id)).all()) if facility_ids else {}
    appointment_counts = dict(db.execute(select(Appointment.facility_id, func.count(Appointment.id)).where(Appointment.facility_id.in_(facility_ids), Appointment.appointment_at >= now, Appointment.appointment_at <= horizon, Appointment.status.in_(_ACTIVE_APPOINTMENT_STATUSES)).group_by(Appointment.facility_id)).all()) if facility_ids else {}
    waiting_counts = dict(db.execute(select(Queue.facility_id, func.count(QueueEntry.id)).join(QueueEntry, QueueEntry.queue_id == Queue.id).where(Queue.facility_id.in_(facility_ids), Queue.status == "ACTIVE", QueueEntry.status == "WAITING").group_by(Queue.facility_id)).all()) if facility_ids else {}

    facilities = [NationalCapacityFacility(facility_id=str(facility_id), facility_code=facility_code, facility_name=facility_name, county=facility_county, departments=int(department_counts.get(facility_id, 0)), scheduled_appointments=int(appointment_counts.get(facility_id, 0)), waiting_queue_entries=int(waiting_counts.get(facility_id, 0))) for facility_id, facility_code, facility_name, facility_county in facility_rows]
    record_audit(db, action="VIEW_NATIONAL_CAPACITY", resource_type="NATIONAL_CAPACITY", result="SUCCESS", user_id=actor_user_id, metadata={"county_filter": county_value, "facility_count": len(facilities), "appointment_horizon_days": 7}, commit=True)
    return NationalCapacityResponse(active_facilities=active_facilities, active_departments=active_departments, scheduled_appointments=scheduled_appointments, waiting_queue_entries=waiting_queue_entries, facilities=facilities)
