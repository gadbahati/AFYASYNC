from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.appointments.schemas import AppointmentCreate, AppointmentResponse, QueueCreate, QueueEntryCreate, QueueEntryResponse, QueueResponse
from app.appointments.service import add_to_queue, create_appointment, create_queue, list_appointments, update_queue_status
from app.auth.dependencies import get_current_user
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
def create(payload: AppointmentCreate, _: User = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        return create_appointment(db, payload.model_dump())
    except ValueError as exc:
        raise _error(exc) from exc


@router.get("", response_model=list[AppointmentResponse])
def list_for_facility(
    facility_id: UUID,
    appointment_date: datetime | None = Query(default=None),
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return list_appointments(db, facility_id, appointment_date)


@router.post("/queues", response_model=QueueResponse, status_code=status.HTTP_201_CREATED)
def create_queue_endpoint(payload: QueueCreate, _: User = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        return create_queue(db, payload.model_dump())
    except ValueError as exc:
        raise _error(exc) from exc


@router.post("/queues/entries", response_model=QueueEntryResponse, status_code=status.HTTP_201_CREATED)
def add_queue_entry(payload: QueueEntryCreate, _: User = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        return add_to_queue(db, payload.model_dump())
    except ValueError as exc:
        raise _error(exc) from exc


@router.patch("/queues/entries/{entry_id}/{new_status}", response_model=QueueEntryResponse)
def change_queue_status(
    entry_id: UUID,
    new_status: str,
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return update_queue_status(db, entry_id, new_status.upper())
    except ValueError as exc:
        raise _error(exc) from exc
