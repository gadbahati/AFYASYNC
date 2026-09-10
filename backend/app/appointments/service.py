from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.appointments.models import Appointment, Queue, QueueEntry
from app.encounters.models import Encounter
from app.facilities.models import Department, Facility
from app.patients.models import Person
from app.rbac.models import Staff


def _require_patient(db: Session, patient_id: UUID) -> Person:
    patient = db.get(Person, patient_id)
    if patient is None or patient.status != "ACTIVE":
        raise ValueError("PATIENT_NOT_FOUND")
    return patient


def _require_facility_department(db: Session, facility_id: UUID, department_id: UUID) -> None:
    facility = db.get(Facility, facility_id)
    department = db.get(Department, department_id)
    if facility is None or facility.status != "ACTIVE":
        raise ValueError("FACILITY_NOT_FOUND")
    if department is None or department.facility_id != facility_id or department.status != "ACTIVE":
        raise ValueError("DEPARTMENT_NOT_FOUND")


def _require_provider(db: Session, provider_id: UUID | None, facility_id: UUID) -> None:
    if provider_id is None:
        return
    provider = db.get(Staff, provider_id)
    if provider is None or provider.facility_id != facility_id or provider.status != "ACTIVE":
        raise ValueError("PROVIDER_NOT_FOUND")


def create_appointment(db: Session, data: dict) -> Appointment:
    _require_patient(db, data["patient_id"])
    _require_facility_department(db, data["facility_id"], data["department_id"])
    _require_provider(db, data.get("provider_id"), data["facility_id"])
    appointment = Appointment(**data)
    db.add(appointment)
    db.commit()
    db.refresh(appointment)
    return appointment


def list_appointments(db: Session, facility_id: UUID, appointment_date: datetime | None = None) -> list[Appointment]:
    stmt = select(Appointment).where(Appointment.facility_id == facility_id)
    if appointment_date:
        start = appointment_date.replace(hour=0, minute=0, second=0, microsecond=0)
        end = start.replace(day=start.day) + __import__("datetime").timedelta(days=1)
        stmt = stmt.where(Appointment.appointment_at >= start, Appointment.appointment_at < end)
    return list(db.scalars(stmt.order_by(Appointment.appointment_at)))


def create_queue(db: Session, data: dict) -> Queue:
    _require_facility_department(db, data["facility_id"], data["department_id"])
    queue = Queue(**data)
    db.add(queue)
    db.commit()
    db.refresh(queue)
    return queue


def add_to_queue(db: Session, data: dict) -> QueueEntry:
    _require_patient(db, data["patient_id"])
    queue = db.get(Queue, data["queue_id"])
    if queue is None or queue.status != "ACTIVE":
        raise ValueError("QUEUE_NOT_FOUND")

    if data.get("appointment_id"):
        appointment = db.get(Appointment, data["appointment_id"])
        if appointment is None or appointment.facility_id != queue.facility_id or appointment.patient_id != data["patient_id"]:
            raise ValueError("INVALID_APPOINTMENT")

    duplicate = db.scalar(
        select(QueueEntry.id).where(
            QueueEntry.queue_id == queue.id,
            QueueEntry.patient_id == data["patient_id"],
            QueueEntry.status.in_(["WAITING", "CALLED", "IN_SERVICE"]),
        ).limit(1)
    )
    if duplicate:
        raise ValueError("PATIENT_ALREADY_QUEUED")

    entry = QueueEntry(**data)
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


def update_queue_status(db: Session, entry_id: UUID, new_status: str) -> QueueEntry:
    entry = db.get(QueueEntry, entry_id)
    if entry is None:
        raise ValueError("QUEUE_ENTRY_NOT_FOUND")

    transitions = {
        "WAITING": {"CALLED", "CANCELLED"},
        "CALLED": {"IN_SERVICE", "CANCELLED", "WAITING"},
        "IN_SERVICE": {"COMPLETED", "CANCELLED"},
        "COMPLETED": set(),
        "CANCELLED": set(),
    }
    if new_status not in transitions.get(entry.status, set()):
        raise ValueError("INVALID_QUEUE_TRANSITION")

    now = datetime.now(timezone.utc)
    entry.status = new_status
    if new_status == "CALLED":
        entry.called_at = now
    if new_status in {"COMPLETED", "CANCELLED"}:
        entry.completed_at = now
    db.commit()
    db.refresh(entry)
    return entry
