from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.appointments.models import Queue, QueueEntry
from app.appointments.schemas import (
    AppointmentCreate,
    AppointmentResponse,
    QueueCreate,
    QueueEntryCreate,
    QueueEntryResponse,
    QueueResponse,
)
from app.appointments.service import add_to_queue, create_appointment, create_queue, list_appointments, update_queue_status
from app.auth.dependencies import get_facility_context, require_permission
from app.database import get_db
from app.rbac.models import User

router = APIRouter(prefix="/api/v1/appointments", tags=["Appointments & Queue"])


def _error(exc: ValueError) -> HTTPException:
    code = str(exc)
    mapping = {
        "PATIENT_NOT_FOUND": 404,
        "FACILITY_NOT_FOUND": 404,
        "DEPARTMENT_NOT_FOUND": 404,
        "PROVIDER_NOT_FOUND": 404,
        "QUEUE_NOT_FOUND": 404,
        "QUEUE_ENTRY_NOT_FOUND": 404,
        "INVALID_APPOINTMENT": 400,
        "PATIENT_ALREADY_QUEUED": 409,
        "INVALID_QUEUE_TRANSITION": 409,
    }
    return HTTPException(status_code=mapping.get(code, 400), detail=code)


@router.post("", response_model=AppointmentResponse, status_code=status.HTTP_201_CREATED)
def create(
    payload: AppointmentCreate,
    user: User = Depends(require_permission("appointments.write")),
    facility_id: UUID = Depends(get_facility_context),
    db: Session = Depends(get_db),
):
    data = payload.model_dump()
    data["facility_id"] = facility_id  # never trust client body for isolation
    try:
        return create_appointment(db, data, actor_user_id=user.id)
    except ValueError as err:
        raise _error(err) from err


@router.get("", response_model=list[AppointmentResponse])
def list_for_facility(
    appointment_date: datetime | None = Query(default=None),
    _: User = Depends(require_permission("appointments.read")),
    facility_id: UUID = Depends(get_facility_context),
    db: Session = Depends(get_db),
):
    return list_appointments(db, facility_id, appointment_date)


@router.post("/queues", response_model=QueueResponse, status_code=status.HTTP_201_CREATED)
def create_queue_endpoint(
    payload: QueueCreate,
    _: User = Depends(require_permission("appointments.write")),
    facility_id: UUID = Depends(get_facility_context),
    db: Session = Depends(get_db),
):
    data = payload.model_dump()
    data["facility_id"] = facility_id
    try:
        return create_queue(db, data)
    except ValueError as err:
        raise _error(err) from err


@router.post("/queues/entries", response_model=QueueEntryResponse, status_code=status.HTTP_201_CREATED)
def add_queue_entry(
    payload: QueueEntryCreate,
    user: User = Depends(require_permission("queue.checkin")),
    facility_id: UUID = Depends(get_facility_context),
    db: Session = Depends(get_db),
):
    entry_queue = db.scalar(select(Queue).where(Queue.id == payload.queue_id))
    if entry_queue is None or entry_queue.facility_id != facility_id:
        raise HTTPException(status_code=403, detail="FACILITY_ACCESS_DENIED")
    try:
        return add_to_queue(db, payload.model_dump(), user.id, actor_user_id=user.id)
    except ValueError as err:
        raise _error(err) from err


@router.patch("/queues/entries/{entry_id}/{new_status}", response_model=QueueEntryResponse)
def change_queue_status(
    entry_id: UUID,
    new_status: str,
    user: User = Depends(require_permission("queue.manage")),
    facility_id: UUID = Depends(get_facility_context),
    db: Session = Depends(get_db),
):
    entry = db.get(QueueEntry, entry_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="QUEUE_ENTRY_NOT_FOUND")
    queue = db.get(Queue, entry.queue_id)
    if queue is None or queue.facility_id != facility_id:
        raise HTTPException(status_code=403, detail="FACILITY_ACCESS_DENIED")
    try:
        return update_queue_status(db, entry_id, new_status.upper(), actor_user_id=user.id)
    except ValueError as err:
        raise _error(err) from err
