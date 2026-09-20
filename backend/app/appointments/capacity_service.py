"""Appointment capacity checks and fairness helpers (hardened)."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from app.appointments.capacity_models import DepartmentCapacity
from app.appointments.models import Appointment
from app.portal.messaging_models import AppointmentRequest

DEFAULT_MAX_PER_DAY = 40
DEFAULT_SLOT_MINUTES = 30
DEFAULT_MAX_PENDING = 80
DEFAULT_OPEN = 8
DEFAULT_CLOSE = 17

# Soft fairness: flag patients with many recent SCHEDULED/COMPLETED appts
RECENT_DAYS = 30
HIGH_USAGE_THRESHOLD = 6


def _day_bounds(day: date) -> tuple[datetime, datetime]:
    start = datetime(day.year, day.month, day.day, tzinfo=timezone.utc)
    end = start + timedelta(days=1)
    return start, end


def get_or_default_capacity(
    db: Session, facility_id: UUID, department_id: UUID
) -> DepartmentCapacity | None:
    row = db.scalar(
        select(DepartmentCapacity).where(
            DepartmentCapacity.facility_id == facility_id,
            DepartmentCapacity.department_id == department_id,
            DepartmentCapacity.status == "ACTIVE",
        )
    )
    return row


def _limits(cap: DepartmentCapacity | None) -> tuple[int, int, int, int, int]:
    if cap is None:
        return DEFAULT_MAX_PER_DAY, DEFAULT_SLOT_MINUTES, DEFAULT_MAX_PENDING, DEFAULT_OPEN, DEFAULT_CLOSE
    return (
        int(cap.max_appointments_per_day),
        int(cap.slot_minutes),
        int(cap.max_pending_requests),
        int(cap.open_hour),
        int(cap.close_hour),
    )


def count_appointments_on_day(
    db: Session, facility_id: UUID, department_id: UUID, day: date
) -> int:
    start, end = _day_bounds(day)
    return int(
        db.scalar(
            select(func.count())
            .select_from(Appointment)
            .where(
                Appointment.facility_id == facility_id,
                Appointment.department_id == department_id,
                Appointment.status.in_(["SCHEDULED", "CHECKED_IN", "IN_PROGRESS", "COMPLETED"]),
                Appointment.appointment_at >= start,
                Appointment.appointment_at < end,
            )
        )
        or 0
    )


def count_pending_requests(db: Session, facility_id: UUID, department_id: UUID | None = None) -> int:
    stmt = select(func.count()).select_from(AppointmentRequest).where(
        AppointmentRequest.facility_id == facility_id,
        AppointmentRequest.status == "PENDING",
    )
    if department_id is not None:
        stmt = stmt.where(
            (AppointmentRequest.department_id == department_id)
            | (AppointmentRequest.department_id.is_(None))
        )
    return int(db.scalar(stmt) or 0)


def assert_capacity_for_slot(
    db: Session,
    *,
    facility_id: UUID,
    department_id: UUID,
    appointment_at: datetime,
) -> None:
    if appointment_at.tzinfo is None:
        appointment_at = appointment_at.replace(tzinfo=timezone.utc)
    now = datetime.now(timezone.utc)
    if appointment_at < now:
        raise ValueError("APPOINTMENT_IN_PAST")

    cap = get_or_default_capacity(db, facility_id, department_id)
    max_day, slot_min, _, open_h, close_h = _limits(cap)
    hour = appointment_at.astimezone(timezone.utc).hour
    if hour < open_h or hour >= close_h:
        raise ValueError("OUTSIDE_OPERATING_HOURS")

    day = appointment_at.astimezone(timezone.utc).date()
    used = count_appointments_on_day(db, facility_id, department_id, day)
    if used >= max_day:
        raise ValueError("DEPARTMENT_DAY_FULL")

    # Slot collision: same department within ± slot_minutes/2 of existing
    half = timedelta(minutes=max(slot_min // 2, 5))
    clash = db.scalar(
        select(Appointment.id)
        .where(
            Appointment.facility_id == facility_id,
            Appointment.department_id == department_id,
            Appointment.status.in_(["SCHEDULED", "CHECKED_IN", "IN_PROGRESS"]),
            Appointment.appointment_at >= appointment_at - half,
            Appointment.appointment_at <= appointment_at + half,
        )
        .limit(1)
    )
    if clash is not None:
        raise ValueError("SLOT_UNAVAILABLE")


def assert_patient_not_double_booked(
    db: Session,
    *,
    patient_id: UUID,
    facility_id: UUID,
    department_id: UUID,
    appointment_at: datetime,
) -> None:
    if appointment_at.tzinfo is None:
        appointment_at = appointment_at.replace(tzinfo=timezone.utc)
    day = appointment_at.astimezone(timezone.utc).date()
    start, end = _day_bounds(day)
    existing = db.scalar(
        select(Appointment.id)
        .where(
            Appointment.patient_id == patient_id,
            Appointment.facility_id == facility_id,
            Appointment.department_id == department_id,
            Appointment.status.in_(["SCHEDULED", "CHECKED_IN", "IN_PROGRESS"]),
            Appointment.appointment_at >= start,
            Appointment.appointment_at < end,
        )
        .limit(1)
    )
    if existing is not None:
        raise ValueError("PATIENT_ALREADY_BOOKED_THAT_DAY")


def assert_pending_capacity(
    db: Session, facility_id: UUID, department_id: UUID | None
) -> None:
    if department_id is None:
        pending = count_pending_requests(db, facility_id, None)
        if pending >= DEFAULT_MAX_PENDING:
            raise ValueError("FACILITY_PENDING_QUEUE_FULL")
        return
    cap = get_or_default_capacity(db, facility_id, department_id)
    _, _, max_pending, _, _ = _limits(cap)
    pending = count_pending_requests(db, facility_id, department_id)
    if pending >= max_pending:
        raise ValueError("DEPARTMENT_PENDING_QUEUE_FULL")


def patient_usage_score(db: Session, patient_id: UUID, facility_id: UUID) -> dict:
    """Fairness advisory: recent booking volume (does not block)."""
    since = datetime.now(timezone.utc) - timedelta(days=RECENT_DAYS)
    count = int(
        db.scalar(
            select(func.count())
            .select_from(Appointment)
            .where(
                Appointment.patient_id == patient_id,
                Appointment.facility_id == facility_id,
                Appointment.created_at >= since,
                Appointment.status.in_(["SCHEDULED", "CHECKED_IN", "COMPLETED", "IN_PROGRESS"]),
            )
        )
        or 0
    )
    return {
        "recent_appointments": count,
        "window_days": RECENT_DAYS,
        "high_usage": count >= HIGH_USAGE_THRESHOLD,
        "fairness_note": (
            "Patient has high recent booking volume — prefer earlier pending requests first"
            if count >= HIGH_USAGE_THRESHOLD
            else "Normal usage"
        ),
    }


def list_day_slots(
    db: Session,
    *,
    facility_id: UUID,
    department_id: UUID,
    day: date,
) -> dict:
    cap = get_or_default_capacity(db, facility_id, department_id)
    max_day, slot_min, _, open_h, close_h = _limits(cap)
    used = count_appointments_on_day(db, facility_id, department_id, day)
    remaining = max(0, max_day - used)

    start, end = _day_bounds(day)
    booked = list(
        db.scalars(
            select(Appointment.appointment_at).where(
                Appointment.facility_id == facility_id,
                Appointment.department_id == department_id,
                Appointment.status.in_(["SCHEDULED", "CHECKED_IN", "IN_PROGRESS"]),
                Appointment.appointment_at >= start,
                Appointment.appointment_at < end,
            )
        )
    )
    booked_set = {b.astimezone(timezone.utc).replace(second=0, microsecond=0) for b in booked}

    slots = []
    cursor = datetime(day.year, day.month, day.day, open_h, 0, tzinfo=timezone.utc)
    day_end = datetime(day.year, day.month, day.day, close_h, 0, tzinfo=timezone.utc)
    now = datetime.now(timezone.utc)
    while cursor < day_end:
        key = cursor.replace(second=0, microsecond=0)
        available = key not in booked_set and key >= now and remaining > 0
        # mark near-collisions
        if available:
            half = timedelta(minutes=max(slot_min // 2, 5))
            for b in booked:
                if abs((b - key).total_seconds()) <= half.total_seconds():
                    available = False
                    break
        slots.append({"at": key.isoformat(), "available": available})
        cursor += timedelta(minutes=slot_min)

    return {
        "facility_id": str(facility_id),
        "department_id": str(department_id),
        "day": day.isoformat(),
        "max_appointments_per_day": max_day,
        "booked": used,
        "remaining": remaining,
        "slot_minutes": slot_min,
        "open_hour": open_h,
        "close_hour": close_h,
        "slots": slots,
    }


def list_pending_fair(
    db: Session, facility_id: UUID, limit: int = 50
) -> list[dict]:
    """PENDING requests FIFO with fairness advisory."""
    rows = list(
        db.scalars(
            select(AppointmentRequest)
            .where(
                AppointmentRequest.facility_id == facility_id,
                AppointmentRequest.status == "PENDING",
            )
            .order_by(AppointmentRequest.created_at.asc())
            .limit(limit)
        )
    )
    out = []
    for i, req in enumerate(rows):
        usage = patient_usage_score(db, req.patient_id, facility_id)
        out.append(
            {
                "id": str(req.id),
                "patient_id": str(req.patient_id),
                "department_id": str(req.department_id) if req.department_id else None,
                "preferred_date": req.preferred_date.isoformat() if req.preferred_date else None,
                "reason": req.reason[:200],
                "created_at": req.created_at.isoformat() if req.created_at else None,
                "fifo_position": i + 1,
                "fairness": usage,
            }
        )
    return out


def upsert_capacity(
    db: Session,
    *,
    facility_id: UUID,
    department_id: UUID,
    max_appointments_per_day: int = 40,
    slot_minutes: int = 30,
    max_pending_requests: int = 80,
    open_hour: int = 8,
    close_hour: int = 17,
) -> DepartmentCapacity:
    if not (1 <= max_appointments_per_day <= 500):
        raise ValueError("INVALID_MAX_PER_DAY")
    if not (5 <= slot_minutes <= 240):
        raise ValueError("INVALID_SLOT_MINUTES")
    if not (0 <= open_hour < close_hour <= 23):
        raise ValueError("INVALID_HOURS")
    row = get_or_default_capacity(db, facility_id, department_id)
    if row is None:
        row = DepartmentCapacity(
            facility_id=facility_id,
            department_id=department_id,
            max_appointments_per_day=max_appointments_per_day,
            slot_minutes=slot_minutes,
            max_pending_requests=max_pending_requests,
            open_hour=open_hour,
            close_hour=close_hour,
            status="ACTIVE",
        )
        db.add(row)
    else:
        row.max_appointments_per_day = max_appointments_per_day
        row.slot_minutes = slot_minutes
        row.max_pending_requests = max_pending_requests
        row.open_hour = open_hour
        row.close_hour = close_hour
        row.status = "ACTIVE"
    db.flush()
    return row
