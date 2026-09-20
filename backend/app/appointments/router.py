from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.appointments.models import Queue, QueueEntry
from app.appointments.schemas import AppointmentCreate, AppointmentResponse, PatientHandoffCreate, QueueCreate, QueueEntryCreate, QueueEntryResponse, QueueResponse
from app.appointments.service import add_to_queue, create_appointment, create_queue, handoff_patient, list_appointments, list_queue_entries, list_queues, update_queue_status
from app.auth.dependencies import get_facility_context, require_permission
from app.database import get_db
from app.encounters.models import Encounter
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
        "ENCOUNTER_NOT_FOUND": 404,
        "ENCOUNTER_CLOSED": 409,
        "INVALID_APPOINTMENT": 400,
        "PATIENT_ALREADY_QUEUED": 409,
        "INVALID_QUEUE_TRANSITION": 409,
        "APPOINTMENT_IN_PAST": 400,
        "OUTSIDE_OPERATING_HOURS": 409,
        "DEPARTMENT_DAY_FULL": 409,
        "SLOT_UNAVAILABLE": 409,
        "PATIENT_ALREADY_BOOKED_THAT_DAY": 409,
        "FACILITY_PENDING_QUEUE_FULL": 409,
        "DEPARTMENT_PENDING_QUEUE_FULL": 409,
        "INVALID_MAX_PER_DAY": 400,
        "INVALID_SLOT_MINUTES": 400,
        "INVALID_HOURS": 400,
    }
    return HTTPException(status_code=mapping.get(code, 400), detail=code)


@router.post("", response_model=AppointmentResponse, status_code=status.HTTP_201_CREATED)
def create(payload: AppointmentCreate, user: User = Depends(require_permission("appointments.write")), facility_id: UUID = Depends(get_facility_context), db: Session = Depends(get_db)):
    data = payload.model_dump(); data["facility_id"] = facility_id
    try: return create_appointment(db, data, actor_user_id=user.id)
    except ValueError as err: raise _error(err) from err


@router.get("", response_model=list[AppointmentResponse])
def list_for_facility(appointment_date: datetime | None = Query(default=None), _: User = Depends(require_permission("appointments.read")), facility_id: UUID = Depends(get_facility_context), db: Session = Depends(get_db)):
    return list_appointments(db, facility_id, appointment_date)


@router.post("/queues", response_model=QueueResponse, status_code=status.HTTP_201_CREATED)
def create_queue_endpoint(payload: QueueCreate, user: User = Depends(require_permission("queue.manage")), facility_id: UUID = Depends(get_facility_context), db: Session = Depends(get_db)):
    data = payload.model_dump(); data["facility_id"] = facility_id
    try: return create_queue(db, data)
    except ValueError as err: raise _error(err) from err


@router.get("/queues", response_model=list[QueueResponse])
def list_queues_endpoint(_: User = Depends(require_permission("queue.manage")), facility_id: UUID = Depends(get_facility_context), db: Session = Depends(get_db)):
    return list_queues(db, facility_id)


@router.get("/queues/entries", response_model=list[QueueEntryResponse])
def list_entries(queue_id: UUID | None = Query(default=None), _: User = Depends(require_permission("queue.manage")), facility_id: UUID = Depends(get_facility_context), db: Session = Depends(get_db)):
    return list_queue_entries(db, facility_id, queue_id)


@router.post("/queues/entries", response_model=QueueEntryResponse, status_code=status.HTTP_201_CREATED)
def enqueue(payload: QueueEntryCreate, user: User = Depends(require_permission("queue.manage")), facility_id: UUID = Depends(get_facility_context), db: Session = Depends(get_db)):
    queue = db.get(Queue, payload.queue_id)
    if queue is None or queue.facility_id != facility_id:
        raise HTTPException(status_code=404, detail="QUEUE_NOT_FOUND")
    try: return add_to_queue(db, payload.model_dump(), created_by=user.id, actor_user_id=user.id)
    except ValueError as err: raise _error(err) from err


@router.post("/handoff", response_model=QueueEntryResponse, status_code=status.HTTP_201_CREATED)
def handoff(payload: PatientHandoffCreate, user: User = Depends(require_permission("queue.manage")), facility_id: UUID = Depends(get_facility_context), db: Session = Depends(get_db)):
    encounter = db.get(Encounter, payload.encounter_id)
    if encounter is None or encounter.facility_id != facility_id or encounter.patient_id != payload.patient_id:
        raise HTTPException(status_code=403, detail="FACILITY_ACCESS_DENIED")
    try: return handoff_patient(db, payload.model_dump(), actor_user_id=user.id)
    except ValueError as err: raise _error(err) from err


@router.patch("/queues/entries/{entry_id}/{new_status}", response_model=QueueEntryResponse)
def change_queue_status(entry_id: UUID, new_status: str, user: User = Depends(require_permission("queue.manage")), facility_id: UUID = Depends(get_facility_context), db: Session = Depends(get_db)):
    entry = db.get(QueueEntry, entry_id)
    if entry is None: raise HTTPException(status_code=404, detail="QUEUE_ENTRY_NOT_FOUND")
    queue = db.get(Queue, entry.queue_id)
    if queue is None or queue.facility_id != facility_id: raise HTTPException(status_code=403, detail="FACILITY_ACCESS_DENIED")
    try: return update_queue_status(db, entry_id, new_status.upper(), actor_user_id=user.id)
    except ValueError as err: raise _error(err) from err


@router.get("/capacity/slots")
def capacity_slots(
    department_id: UUID,
    day: str = Query(..., description="YYYY-MM-DD"),
    user: User = Depends(require_permission("appointments.read")),
    facility_id: UUID = Depends(get_facility_context),
    db: Session = Depends(get_db),
):
    """List slot availability for a department day."""
    from datetime import date as date_cls

    from app.appointments.capacity_service import list_day_slots

    try:
        d = date_cls.fromisoformat(day)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="INVALID_DAY") from exc
    return list_day_slots(db, facility_id=facility_id, department_id=department_id, day=d)


@router.get("/capacity/pending-fair")
def capacity_pending_fair(
    limit: int = Query(default=50, ge=1, le=200),
    user: User = Depends(require_permission("appointments.read")),
    facility_id: UUID = Depends(get_facility_context),
    db: Session = Depends(get_db),
):
    """FIFO pending requests with fairness advisory."""
    from app.appointments.capacity_service import list_pending_fair

    return list_pending_fair(db, facility_id, limit=limit)


@router.put("/capacity/department/{department_id}")
def set_department_capacity(
    department_id: UUID,
    max_appointments_per_day: int = Query(default=40, ge=1, le=500),
    slot_minutes: int = Query(default=30, ge=5, le=240),
    max_pending_requests: int = Query(default=80, ge=1, le=500),
    open_hour: int = Query(default=8, ge=0, le=22),
    close_hour: int = Query(default=17, ge=1, le=23),
    user: User = Depends(require_permission("appointments.write")),
    facility_id: UUID = Depends(get_facility_context),
    db: Session = Depends(get_db),
):
    from app.appointments.capacity_service import upsert_capacity
    from app.audit.service import record_audit
    from app.facilities.models import Department

    dept = db.get(Department, department_id)
    if dept is None or dept.facility_id != facility_id:
        raise HTTPException(status_code=404, detail="DEPARTMENT_NOT_FOUND")
    try:
        row = upsert_capacity(
            db,
            facility_id=facility_id,
            department_id=department_id,
            max_appointments_per_day=max_appointments_per_day,
            slot_minutes=slot_minutes,
            max_pending_requests=max_pending_requests,
            open_hour=open_hour,
            close_hour=close_hour,
        )
    except ValueError as err:
        raise _error(err) from err
    record_audit(
        db,
        action="DEPARTMENT_CAPACITY_UPSERT",
        resource_type="DEPARTMENT",
        resource_id=str(department_id),
        result="SUCCESS",
        user_id=user.id,
        facility_id=facility_id,
        metadata={
            "max_per_day": max_appointments_per_day,
            "slot_minutes": slot_minutes,
        },
        commit=False,
    )
    db.commit()
    return {
        "id": str(row.id),
        "department_id": str(row.department_id),
        "max_appointments_per_day": row.max_appointments_per_day,
        "slot_minutes": row.slot_minutes,
        "max_pending_requests": row.max_pending_requests,
        "open_hour": row.open_hour,
        "close_hour": row.close_hour,
        "status": row.status,
    }
