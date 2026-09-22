"""Tele-consult request lifecycle — patient request, facility reply."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit.service import record_audit
from app.facilities.models import Facility
from app.patients.models import Person
from app.rbac.models import Staff
from app.telemedicine.models import TeleConsultRequest

ALLOWED_URGENCY = {"ROUTINE", "URGENT"}
OPEN_STATUSES = {"REQUESTED", "ACCEPTED"}


class TeleError(ValueError):
    pass


def _ser(r: TeleConsultRequest) -> dict:
    return {
        "id": str(r.id),
        "person_id": str(r.person_id),
        "facility_id": str(r.facility_id),
        "reason": r.reason,
        "urgency": r.urgency,
        "status": r.status,
        "preferred_window": r.preferred_window,
        "scheduled_at": r.scheduled_at.isoformat() if r.scheduled_at else None,
        "facility_message": r.facility_message,
        "clinical_summary": r.clinical_summary,
        "created_at": r.created_at.isoformat() if r.created_at else None,
        "updated_at": r.updated_at.isoformat() if r.updated_at else None,
    }


def patient_request(
    db: Session,
    *,
    person_id: UUID,
    facility_id: UUID,
    reason: str,
    urgency: str = "ROUTINE",
    preferred_window: str | None = None,
    actor_user_id: UUID | None = None,
) -> TeleConsultRequest:
    if db.get(Person, person_id) is None:
        raise TeleError("PERSON_NOT_FOUND")
    fac = db.get(Facility, facility_id)
    if fac is None or fac.status != "ACTIVE":
        raise TeleError("FACILITY_NOT_AVAILABLE")

    urg = (urgency or "ROUTINE").strip().upper()
    if urg not in ALLOWED_URGENCY:
        raise TeleError("INVALID_URGENCY")
    text = reason.strip()[:500]
    if len(text) < 5:
        raise TeleError("REASON_TOO_SHORT")

    # Prevent spam: one open request per person+facility
    existing = db.scalar(
        select(TeleConsultRequest).where(
            TeleConsultRequest.person_id == person_id,
            TeleConsultRequest.facility_id == facility_id,
            TeleConsultRequest.status.in_(list(OPEN_STATUSES)),
        )
    )
    if existing:
        raise TeleError("OPEN_REQUEST_EXISTS")

    req = TeleConsultRequest(
        person_id=person_id,
        facility_id=facility_id,
        reason=text,
        urgency=urg,
        preferred_window=(preferred_window or "").strip()[:120] or None,
        status="REQUESTED",
    )
    db.add(req)
    db.flush()
    record_audit(
        db,
        action="TELE_CONSULT_REQUEST",
        resource_type="TELE_CONSULT",
        resource_id=str(req.id),
        result="REQUESTED",
        user_id=actor_user_id,
        facility_id=facility_id,
        metadata={"urgency": urg},
        commit=False,
    )
    return req


def list_patient(db: Session, *, person_id: UUID, limit: int = 30) -> list[dict]:
    limit = max(1, min(limit, 100))
    rows = db.scalars(
        select(TeleConsultRequest)
        .where(TeleConsultRequest.person_id == person_id)
        .order_by(TeleConsultRequest.created_at.desc())
        .limit(limit)
    ).all()
    return [_ser(r) for r in rows]


def list_facility(db: Session, *, facility_id: UUID, status: str | None = None, limit: int = 50) -> list[dict]:
    limit = max(1, min(limit, 100))
    q = select(TeleConsultRequest).where(TeleConsultRequest.facility_id == facility_id)
    if status:
        q = q.where(TeleConsultRequest.status == status.strip().upper())
    rows = db.scalars(q.order_by(TeleConsultRequest.created_at.asc()).limit(limit)).all()
    return [_ser(r) for r in rows]


def facility_respond(
    db: Session,
    *,
    facility_id: UUID,
    request_id: UUID,
    decision: str,
    facility_message: str | None = None,
    scheduled_at: datetime | None = None,
    staff_id: UUID | None = None,
    actor_user_id: UUID | None = None,
) -> TeleConsultRequest:
    req = db.get(TeleConsultRequest, request_id)
    if req is None or req.facility_id != facility_id:
        raise TeleError("REQUEST_NOT_FOUND")
    if req.status != "REQUESTED":
        raise TeleError("INVALID_STATUS")

    dec = decision.strip().upper()
    if dec not in {"ACCEPTED", "DENIED"}:
        raise TeleError("INVALID_DECISION")

    if staff_id is not None:
        staff = db.get(Staff, staff_id)
        if staff is None or staff.facility_id != facility_id:
            raise TeleError("STAFF_NOT_FOUND")
        req.handled_by_staff_id = staff_id

    req.status = dec
    req.facility_message = (facility_message or "").strip()[:500] or None
    if dec == "ACCEPTED":
        req.scheduled_at = scheduled_at or datetime.now(timezone.utc)
    db.flush()
    record_audit(
        db,
        action="TELE_CONSULT_RESPOND",
        resource_type="TELE_CONSULT",
        resource_id=str(req.id),
        result=dec,
        user_id=actor_user_id,
        facility_id=facility_id,
        commit=False,
    )
    return req


def complete_consult(
    db: Session,
    *,
    facility_id: UUID,
    request_id: UUID,
    clinical_summary: str,
    actor_user_id: UUID | None = None,
) -> TeleConsultRequest:
    req = db.get(TeleConsultRequest, request_id)
    if req is None or req.facility_id != facility_id:
        raise TeleError("REQUEST_NOT_FOUND")
    if req.status != "ACCEPTED":
        raise TeleError("INVALID_STATUS")
    summary = clinical_summary.strip()[:4000]
    if len(summary) < 3:
        raise TeleError("SUMMARY_REQUIRED")
    req.status = "COMPLETED"
    req.clinical_summary = summary
    db.flush()
    record_audit(
        db,
        action="TELE_CONSULT_COMPLETE",
        resource_type="TELE_CONSULT",
        resource_id=str(req.id),
        result="COMPLETED",
        user_id=actor_user_id,
        facility_id=facility_id,
        commit=False,
    )
    return req


def patient_cancel(
    db: Session,
    *,
    person_id: UUID,
    request_id: UUID,
    actor_user_id: UUID | None = None,
) -> TeleConsultRequest:
    req = db.get(TeleConsultRequest, request_id)
    if req is None or req.person_id != person_id:
        raise TeleError("REQUEST_NOT_FOUND")
    if req.status not in OPEN_STATUSES:
        raise TeleError("INVALID_STATUS")
    req.status = "CANCELLED"
    db.flush()
    record_audit(
        db,
        action="TELE_CONSULT_CANCEL",
        resource_type="TELE_CONSULT",
        resource_id=str(req.id),
        result="CANCELLED",
        user_id=actor_user_id,
        facility_id=req.facility_id,
        commit=False,
    )
    return req
