"""Ambulance request lifecycle."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.ambulance.models import AmbulanceRequest
from app.audit.service import record_audit
from app.facilities.models import Facility
from app.rbac.models import Staff

PRIORITIES = {"CRITICAL", "URGENT", "ROUTINE"}
OPEN = {"REQUESTED", "DISPATCHED", "EN_ROUTE", "ARRIVED"}
TRANSITIONS = {
    "REQUESTED": {"DISPATCHED", "DENIED", "CANCELLED"},
    "DISPATCHED": {"EN_ROUTE", "CANCELLED"},
    "EN_ROUTE": {"ARRIVED", "CANCELLED"},
    "ARRIVED": {"COMPLETED", "CANCELLED"},
}


class AmbulanceError(ValueError):
    pass


def _ser(r: AmbulanceRequest) -> dict:
    return {
        "id": str(r.id),
        "person_id": str(r.person_id) if r.person_id else None,
        "facility_id": str(r.facility_id),
        "requester_phone": r.requester_phone,
        "pickup_location": r.pickup_location,
        "destination": r.destination,
        "clinical_note": r.clinical_note,
        "priority": r.priority,
        "status": r.status,
        "vehicle_ref": r.vehicle_ref,
        "eta_minutes": r.eta_minutes,
        "dispatcher_message": r.dispatcher_message,
        "outcome_note": r.outcome_note,
        "created_at": r.created_at.isoformat() if r.created_at else None,
        "updated_at": r.updated_at.isoformat() if r.updated_at else None,
    }


def create_request(
    db: Session,
    *,
    facility_id: UUID,
    requester_phone: str,
    pickup_location: str,
    destination: str | None = None,
    clinical_note: str | None = None,
    priority: str = "URGENT",
    person_id: UUID | None = None,
    actor_user_id: UUID | None = None,
) -> AmbulanceRequest:
    fac = db.get(Facility, facility_id)
    if fac is None or fac.status != "ACTIVE":
        raise AmbulanceError("FACILITY_NOT_AVAILABLE")

    phone = requester_phone.strip()[:30]
    if len(phone) < 7:
        raise AmbulanceError("PHONE_REQUIRED")
    pickup = pickup_location.strip()[:300]
    if len(pickup) < 3:
        raise AmbulanceError("PICKUP_REQUIRED")

    pri = (priority or "URGENT").strip().upper()
    if pri not in PRIORITIES:
        raise AmbulanceError("INVALID_PRIORITY")

    req = AmbulanceRequest(
        facility_id=facility_id,
        person_id=person_id,
        requester_phone=phone,
        pickup_location=pickup,
        destination=(destination or "").strip()[:300] or None,
        clinical_note=(clinical_note or "").strip()[:500] or None,
        priority=pri,
        status="REQUESTED",
    )
    db.add(req)
    db.flush()
    record_audit(
        db,
        action="AMBULANCE_REQUEST",
        resource_type="AMBULANCE",
        resource_id=str(req.id),
        result="REQUESTED",
        user_id=actor_user_id,
        facility_id=facility_id,
        metadata={"priority": pri},
        commit=False,
    )
    return req


def list_facility(
    db: Session, *, facility_id: UUID, status: str | None = None, limit: int = 50
) -> list[dict]:
    limit = max(1, min(limit, 100))
    q = select(AmbulanceRequest).where(AmbulanceRequest.facility_id == facility_id)
    if status:
        q = q.where(AmbulanceRequest.status == status.strip().upper())
    rows = db.scalars(
        q.order_by(
            # CRITICAL first among open
            AmbulanceRequest.created_at.asc()
        ).limit(limit)
    ).all()
    # sort in Python: CRITICAL, URGENT, ROUTINE among open
    order = {"CRITICAL": 0, "URGENT": 1, "ROUTINE": 2}

    def key(r: AmbulanceRequest):
        open_rank = 0 if r.status in OPEN else 1
        return (open_rank, order.get(r.priority, 9), r.created_at or datetime.min.replace(tzinfo=timezone.utc))

    rows = sorted(rows, key=key)
    return [_ser(r) for r in rows]


def list_patient(db: Session, *, person_id: UUID, limit: int = 30) -> list[dict]:
    limit = max(1, min(limit, 100))
    rows = db.scalars(
        select(AmbulanceRequest)
        .where(AmbulanceRequest.person_id == person_id)
        .order_by(AmbulanceRequest.created_at.desc())
        .limit(limit)
    ).all()
    return [_ser(r) for r in rows]


def update_status(
    db: Session,
    *,
    facility_id: UUID,
    request_id: UUID,
    new_status: str,
    vehicle_ref: str | None = None,
    eta_minutes: float | None = None,
    dispatcher_message: str | None = None,
    outcome_note: str | None = None,
    staff_id: UUID | None = None,
    actor_user_id: UUID | None = None,
) -> AmbulanceRequest:
    req = db.get(AmbulanceRequest, request_id)
    if req is None or req.facility_id != facility_id:
        raise AmbulanceError("REQUEST_NOT_FOUND")

    ns = new_status.strip().upper()
    allowed = TRANSITIONS.get(req.status, set())
    if ns not in allowed:
        raise AmbulanceError(f"INVALID_TRANSITION:{req.status}->{ns}")

    if staff_id is not None:
        staff = db.get(Staff, staff_id)
        if staff is None or staff.facility_id != facility_id:
            raise AmbulanceError("STAFF_NOT_FOUND")
        req.handled_by_staff_id = staff_id

    req.status = ns
    if vehicle_ref is not None:
        req.vehicle_ref = vehicle_ref.strip()[:80] or None
    if eta_minutes is not None:
        req.eta_minutes = float(eta_minutes)
    if dispatcher_message is not None:
        req.dispatcher_message = dispatcher_message.strip()[:500] or None
    if outcome_note is not None:
        req.outcome_note = outcome_note.strip()[:4000] or None

    db.flush()
    record_audit(
        db,
        action="AMBULANCE_STATUS",
        resource_type="AMBULANCE",
        resource_id=str(req.id),
        result=ns,
        user_id=actor_user_id,
        facility_id=facility_id,
        commit=False,
    )
    return req


def board_summary(db: Session, *, facility_id: UUID | None = None) -> dict:
    q = select(AmbulanceRequest.status, func.count()).group_by(AmbulanceRequest.status)
    if facility_id:
        q = q.where(AmbulanceRequest.facility_id == facility_id)
    counts = {str(s): int(c) for s, c in db.execute(q).all()}
    open_count = sum(counts.get(s, 0) for s in OPEN)
    return {
        "facility_id": str(facility_id) if facility_id else None,
        "open_count": open_count,
        "by_status": counts,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "developer": "BAHATI GAD WANGWE",
    }
