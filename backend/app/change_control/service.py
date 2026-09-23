"""Change request lifecycle + release registry."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit.service import record_audit
from app.change_control.models import ChangeRequest, ReleaseRecord

CHANGE_TYPES = {"STANDARD", "EMERGENCY", "MAJOR"}
RISK_LEVELS = {"LOW", "MEDIUM", "HIGH", "CRITICAL"}
CHANGE_STATUSES = {"DRAFT", "SUBMITTED", "APPROVED", "REJECTED", "IMPLEMENTED", "ROLLED_BACK"}
RELEASE_ENVS = {"staging", "production"}
RELEASE_STATUSES = {"PLANNED", "DEPLOYED", "VERIFIED", "ROLLED_BACK"}


class ChangeError(ValueError):
    pass


def governance_policy() -> dict:
    return {
        "title": "AfyaSync national change-control policy",
        "rules": [
            "All production releases should link to an APPROVED change request (except documented emergencies)",
            "EMERGENCY changes require post-implementation review within 72 hours",
            "HIGH/CRITICAL risk requires dual approval in operational process (recorded in notes)",
            "Staging deploy before production for STANDARD and MAJOR changes",
            "Rollback path must be noted for MAJOR releases",
        ],
        "status_machine": list(CHANGE_STATUSES),
        "developer": "BAHATI GAD WANGWE",
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def create_change(
    db: Session,
    *,
    title: str,
    description: str,
    change_type: str = "STANDARD",
    risk_level: str = "MEDIUM",
    actor_user_id: UUID | None = None,
) -> ChangeRequest:
    ct = (change_type or "STANDARD").strip().upper()
    rl = (risk_level or "MEDIUM").strip().upper()
    if ct not in CHANGE_TYPES:
        raise ChangeError("INVALID_CHANGE_TYPE")
    if rl not in RISK_LEVELS:
        raise ChangeError("INVALID_RISK_LEVEL")
    t = title.strip()
    d = description.strip()
    if len(t) < 3 or len(d) < 5:
        raise ChangeError("TITLE_AND_DESCRIPTION_REQUIRED")

    row = ChangeRequest(
        title=t[:200],
        description=d[:5000],
        change_type=ct,
        risk_level=rl,
        status="DRAFT",
        requested_by_user_id=actor_user_id,
    )
    db.add(row)
    db.flush()
    record_audit(
        db,
        action="CHANGE_REQUEST_CREATE",
        resource_type="CHANGE_REQUEST",
        resource_id=str(row.id),
        result="DRAFT",
        user_id=actor_user_id,
        metadata={"change_type": ct, "risk_level": rl},
        commit=False,
    )
    return row


def transition_change(
    db: Session,
    *,
    change_id: UUID,
    status: str,
    decision_notes: str | None = None,
    actor_user_id: UUID | None = None,
) -> ChangeRequest:
    row = db.get(ChangeRequest, change_id)
    if row is None:
        raise ChangeError("CHANGE_NOT_FOUND")
    st = status.strip().upper()
    if st not in CHANGE_STATUSES:
        raise ChangeError("INVALID_STATUS")

    # Simple allowed transitions
    allowed = {
        "DRAFT": {"SUBMITTED", "REJECTED"},
        "SUBMITTED": {"APPROVED", "REJECTED", "DRAFT"},
        "APPROVED": {"IMPLEMENTED", "ROLLED_BACK", "REJECTED"},
        "IMPLEMENTED": {"ROLLED_BACK"},
        "REJECTED": {"DRAFT"},
        "ROLLED_BACK": {"DRAFT"},
    }
    if st not in allowed.get(row.status, set()) and st != row.status:
        raise ChangeError(f"INVALID_TRANSITION:{row.status}->{st}")

    row.status = st
    if decision_notes is not None:
        row.decision_notes = decision_notes.strip()[:2000] or None
    if st in {"APPROVED", "REJECTED"}:
        row.approved_by_user_id = actor_user_id
        row.decided_at = datetime.now(timezone.utc)
    db.flush()
    record_audit(
        db,
        action="CHANGE_REQUEST_TRANSITION",
        resource_type="CHANGE_REQUEST",
        resource_id=str(row.id),
        result=st,
        user_id=actor_user_id,
        commit=False,
    )
    return row


def list_changes(db: Session, *, status: str | None = None, limit: int = 50) -> list[dict]:
    limit = max(1, min(limit, 200))
    q = select(ChangeRequest)
    if status:
        q = q.where(ChangeRequest.status == status.strip().upper())
    rows = db.scalars(q.order_by(ChangeRequest.created_at.desc()).limit(limit)).all()
    return [
        {
            "id": str(r.id),
            "title": r.title,
            "change_type": r.change_type,
            "risk_level": r.risk_level,
            "status": r.status,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]


def record_release(
    db: Session,
    *,
    version: str,
    environment: str = "staging",
    status: str = "PLANNED",
    notes: str | None = None,
    change_request_id: UUID | None = None,
    actor_user_id: UUID | None = None,
) -> ReleaseRecord:
    ver = version.strip()
    env = (environment or "staging").strip().lower()
    st = (status or "PLANNED").strip().upper()
    if not ver:
        raise ChangeError("VERSION_REQUIRED")
    if env not in RELEASE_ENVS:
        raise ChangeError("INVALID_ENVIRONMENT")
    if st not in RELEASE_STATUSES:
        raise ChangeError("INVALID_RELEASE_STATUS")

    if change_request_id is not None:
        cr = db.get(ChangeRequest, change_request_id)
        if cr is None:
            raise ChangeError("CHANGE_NOT_FOUND")
        if env == "production" and cr.status not in {"APPROVED", "IMPLEMENTED"} and cr.change_type != "EMERGENCY":
            raise ChangeError("PRODUCTION_REQUIRES_APPROVED_CHANGE")

    row = ReleaseRecord(
        version=ver[:40],
        environment=env,
        status=st,
        notes=(notes or "").strip()[:2000] or None,
        change_request_id=change_request_id,
        deployed_by_user_id=actor_user_id,
        deployed_at=datetime.now(timezone.utc) if st in {"DEPLOYED", "VERIFIED"} else None,
    )
    db.add(row)
    db.flush()
    record_audit(
        db,
        action="RELEASE_RECORD",
        resource_type="RELEASE_RECORD",
        resource_id=str(row.id),
        result=st,
        user_id=actor_user_id,
        metadata={"version": ver, "environment": env},
        commit=False,
    )
    return row


def list_releases(db: Session, *, limit: int = 30) -> list[dict]:
    limit = max(1, min(limit, 100))
    rows = db.scalars(
        select(ReleaseRecord).order_by(ReleaseRecord.created_at.desc()).limit(limit)
    ).all()
    return [
        {
            "id": str(r.id),
            "version": r.version,
            "environment": r.environment,
            "status": r.status,
            "change_request_id": str(r.change_request_id) if r.change_request_id else None,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "deployed_at": r.deployed_at.isoformat() if r.deployed_at else None,
        }
        for r in rows
    ]
