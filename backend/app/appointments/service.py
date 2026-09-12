from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.appointments.models import Appointment, Queue, QueueEntry
from app.encounters.service import create_encounter
from app.facilities.models import Department, Facility
from app.notifications.events import notify_patient_event
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


def create_appointment(db: Session, data: dict, actor_user_id: UUID | None = None) -> Appointment:
    _require_patient(db, data["patient_id"])
    _require_facility_department(db, data["facility_id"], data["department_id"])
    _require_provider(db, data.get("provider_id"), data["facility_id"])
    appointment = Appointment(**data)
    db.add(appointment)
    db.flush()
    notify_patient_event(
        db,
        patient_id=appointment.patient_id,
        facility_id=appointment.facility_id,
        event_type="APPOINTMENT_CONFIRMED",
        action_url=f"/appointments/{appointment.id}",
        metadata={"appointment_id": str(appointment.id)},
        actor_user_id=actor_user_id,
        commit=False,
    )
    db.commit()
    db.refresh(appointment)
    return appointment


def list_appointments(db: Session, facility_id: UUID, appointment_date: datetime | None = None) -> list[Appointment]:
    stmt = select(Appointment).where(Appointment.facility_id == facility_id)
    if appointment_date:
        start = appointment_date.replace(hour=0, minute=0, second=0, microsecond=0)
        end = start + timedelta(days=1)
        stmt = stmt.where(Appointment.appointment_at >= start, Appointment.appointment_at < end)
    return list(db.scalars(stmt.order_by(Appointment.appointment_at)))


def create_queue(db: Session, data: dict) -> Queue:
    _require_facility_department(db, data["facility_id"], data["department_id"])
    queue = Queue(**data)
    db.add(queue)
    db.commit()
    db.refresh(queue)
    return queue


def list_queues(db: Session, facility_id: UUID) -> list[Queue]:
    return list(
        db.scalars(
            select(Queue)
            .where(Queue.facility_id == facility_id)
            .order_by(Queue.name)
        )
    )


def list_queue_entries(db: Session, facility_id: UUID, queue_id: UUID | None = None) -> list[QueueEntry]:
    stmt = (
        select(QueueEntry)
        .join(Queue, Queue.id == QueueEntry.queue_id)
        .where(Queue.facility_id == facility_id)
    )
    if queue_id is not None:
        stmt = stmt.where(QueueEntry.queue_id == queue_id)
    return list(db.scalars(stmt.order_by(QueueEntry.queued_at.desc())))


def add_to_queue(db: Session, data: dict, created_by: UUID, actor_user_id: UUID | None = None) -> QueueEntry:
    _require_patient(db, data["patient_id"])
    queue = db.get(Queue, data["queue_id"])
    if queue is None or queue.status != "ACTIVE":
        raise ValueError("QUEUE_NOT_FOUND")

    if data.get("appointment_id"):
        appointment = db.get(Appointment, data["appointment_id"])
        if (
            appointment is None
            or appointment.facility_id != queue.facility_id
            or appointment.patient_id != data["patient_id"]
        ):
            raise ValueError("INVALID_APPOINTMENT")

    duplicate = db.scalar(
        select(QueueEntry.id)
        .where(
            QueueEntry.queue_id == queue.id,
            QueueEntry.patient_id == data["patient_id"],
            QueueEntry.status.in_(["WAITING", "CALLED", "IN_SERVICE"]),
        )
        .limit(1)
    )
    if duplicate:
        raise ValueError("PATIENT_ALREADY_QUEUED")

    entry = QueueEntry(**data)
    db.add(entry)
    db.flush()

    encounter = create_encounter(
        db,
        {
            "patient_id": data["patient_id"],
            "facility_id": queue.facility_id,
            "department_id": queue.department_id,
            "encounter_type": "OUTPATIENT",
            "reason": "Queue check-in",
        },
        created_by,
        commit=False,
    )
    entry.encounter_id = encounter.id
    notify_patient_event(
        db,
        patient_id=entry.patient_id,
        facility_id=queue.facility_id,
        event_type="QUEUE_CHECKIN",
        action_url=f"/queue/{entry.id}",
        metadata={"queue_entry_id": str(entry.id), "encounter_id": str(encounter.id)},
        actor_user_id=actor_user_id,
        commit=False,
    )
    db.commit()
    db.refresh(entry)
    return entry


def update_queue_status(db: Session, entry_id: UUID, new_status: str, actor_user_id: UUID | None = None) -> QueueEntry:
    entry = db.get(QueueEntry, entry_id)
    if entry is None:
        raise ValueError("QUEUE_ENTRY_NOT_FOUND")

    queue = db.get(Queue, entry.queue_id)
    if queue is None:
        raise ValueError("QUEUE_NOT_FOUND")

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

    notify_patient_event(
        db,
        patient_id=entry.patient_id,
        facility_id=queue.facility_id,
        event_type="QUEUE_STATUS_CHANGED",
        action_url=f"/queue/{entry.id}",
        metadata={"status": new_status},
        actor_user_id=actor_user_id,
        commit=False,
    )
    db.commit()
    db.refresh(entry)
    return entry
