"""Retention catalogue + erasure request workflow (pseudonymise, do not destroy claims)."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit.service import record_audit
from app.patients.models import Person
from app.retention.models import ErasureRequest

RETENTION_POLICIES = [
    {
        "class": "CLINICAL_ENCOUNTER",
        "retention": "Minimum 7 years after last encounter (or longer if law requires)",
        "archive": "Cold storage after active care ends",
        "erasure": "Not deleted wholesale — pseudonymise identifiers when erasure upheld",
    },
    {
        "class": "CLAIMS_FINANCIAL",
        "retention": "Aligned to SHA/finance retention (typically 7+ years)",
        "archive": "Immutable claim artefacts retained for audit",
        "erasure": "Restricted — financial audit trail preserved",
    },
    {
        "class": "AUDIT_LOG",
        "retention": "Minimum 3 years",
        "archive": "Append-only",
        "erasure": "Not subject to subject-requested deletion of the log itself",
    },
    {
        "class": "PORTAL_MESSAGING",
        "retention": "2 years after last message",
        "archive": "Optional",
        "erasure": "May be purged after legal hold clearance",
    },
    {
        "class": "CONSENT_RECORDS",
        "retention": "Life of care relationship + statutory period",
        "archive": "Yes",
        "erasure": "Evidence of consent decision retained even if clinical detail restricted",
    },
]

REQUEST_TYPES = {"ERASURE", "RESTRICTION", "ACCESS_EXPORT"}
STATUSES = {"RECEIVED", "UNDER_REVIEW", "FULFILLED", "REJECTED", "CANCELLED"}


class RetentionError(ValueError):
    pass


def retention_catalogue() -> dict:
    return {
        "policies": RETENTION_POLICIES,
        "legal_note": "Kenya Data Protection Act — controllers must balance erasure rights with legal retention duties",
        "developer": "BAHATI GAD WANGWE",
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def _ser(r: ErasureRequest) -> dict:
    return {
        "id": str(r.id),
        "person_id": str(r.person_id),
        "facility_id": str(r.facility_id) if r.facility_id else None,
        "request_type": r.request_type,
        "status": r.status,
        "reason": r.reason,
        "decision_notes": r.decision_notes,
        "created_at": r.created_at.isoformat() if r.created_at else None,
        "fulfilled_at": r.fulfilled_at.isoformat() if r.fulfilled_at else None,
    }


def create_request(
    db: Session,
    *,
    person_id: UUID,
    request_type: str = "ERASURE",
    reason: str | None = None,
    facility_id: UUID | None = None,
    actor_user_id: UUID | None = None,
) -> ErasureRequest:
    if db.get(Person, person_id) is None:
        raise RetentionError("PERSON_NOT_FOUND")
    rt = (request_type or "ERASURE").strip().upper()
    if rt not in REQUEST_TYPES:
        raise RetentionError("INVALID_REQUEST_TYPE")

    req = ErasureRequest(
        person_id=person_id,
        facility_id=facility_id,
        request_type=rt,
        status="RECEIVED",
        reason=(reason or "").strip()[:2000] or None,
        requested_by_user_id=actor_user_id,
    )
    db.add(req)
    db.flush()
    record_audit(
        db,
        action="ERASURE_REQUEST_CREATE",
        resource_type="ERASURE_REQUEST",
        resource_id=str(req.id),
        result="RECEIVED",
        user_id=actor_user_id,
        facility_id=facility_id,
        patient_id=person_id,
        metadata={"request_type": rt},
        commit=False,
    )
    return req


def decide_request(
    db: Session,
    *,
    request_id: UUID,
    status: str,
    decision_notes: str | None = None,
    actor_user_id: UUID | None = None,
    apply_pseudonym: bool = False,
) -> ErasureRequest:
    req = db.get(ErasureRequest, request_id)
    if req is None:
        raise RetentionError("REQUEST_NOT_FOUND")

    st = status.strip().upper()
    if st not in STATUSES:
        raise RetentionError("INVALID_STATUS")

    req.status = st
    if decision_notes is not None:
        req.decision_notes = decision_notes.strip()[:2000] or None
    req.decided_by_user_id = actor_user_id

    if st == "FULFILLED" and req.request_type == "ERASURE" and apply_pseudonym:
        person = db.get(Person, req.person_id)
        if person is not None:
            # Pseudonymise direct identifiers — keep row for referential integrity
            person.first_name = "REDACTED"
            person.last_name = "REDACTED"
            if getattr(person, "middle_name", None) is not None:
                person.middle_name = None
            if hasattr(person, "phone") and person.phone:
                person.phone = None
            if hasattr(person, "email") and person.email:
                person.email = None
            if hasattr(person, "status"):
                person.status = "RESTRICTED"
            req.fulfilled_at = datetime.now(timezone.utc)

    if st == "FULFILLED" and req.fulfilled_at is None:
        req.fulfilled_at = datetime.now(timezone.utc)

    db.flush()
    record_audit(
        db,
        action="ERASURE_REQUEST_DECIDE",
        resource_type="ERASURE_REQUEST",
        resource_id=str(req.id),
        result=st,
        user_id=actor_user_id,
        facility_id=req.facility_id,
        patient_id=req.person_id,
        metadata={"apply_pseudonym": apply_pseudonym},
        commit=False,
    )
    return req


def list_requests(
    db: Session,
    *,
    facility_id: UUID | None = None,
    status: str | None = None,
    limit: int = 50,
) -> list[dict]:
    limit = max(1, min(limit, 200))
    q = select(ErasureRequest)
    if facility_id is not None:
        q = q.where(ErasureRequest.facility_id == facility_id)
    if status:
        q = q.where(ErasureRequest.status == status.strip().upper())
    rows = db.scalars(q.order_by(ErasureRequest.created_at.desc()).limit(limit)).all()
    return [_ser(r) for r in rows]
