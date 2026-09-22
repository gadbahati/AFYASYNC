"""Offline resilience APIs — outbox enqueue, drain, stats, connectivity."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth.dependencies import get_facility_context, require_permission
from app.database import get_db
from app.offline.service import (
    OfflineError,
    drain_outbox,
    enqueue_event,
    list_pending,
    outbox_stats,
    record_connectivity_probe,
)
from app.rbac.models import User

router = APIRouter(prefix="/api/v1/offline", tags=["Offline Resilience"])


class EnqueueBody(BaseModel):
    event_type: str = Field(min_length=3, max_length=80)
    payload: dict = Field(default_factory=dict)
    idempotency_key: str = Field(min_length=4, max_length=120)


class ProbeBody(BaseModel):
    target: str = Field(min_length=2, max_length=200)
    ok: bool
    latency_ms: int | None = Field(default=None, ge=0, le=120_000)
    detail: str | None = Field(default=None, max_length=300)


@router.get("/stats")
def stats(
    db: Session = Depends(get_db),
    facility_id: UUID = Depends(get_facility_context),
    user: User = Depends(require_permission("reports.read")),
):
    _ = user
    return outbox_stats(db, facility_id=facility_id)


@router.get("/pending")
def pending(
    db: Session = Depends(get_db),
    facility_id: UUID = Depends(get_facility_context),
    user: User = Depends(require_permission("reports.read")),
    limit: int = 50,
):
    _ = user
    events = list_pending(db, facility_id=facility_id, limit=limit)
    return {
        "count": len(events),
        "events": [
            {
                "id": str(e.id),
                "event_type": e.event_type,
                "status": e.status,
                "attempts": e.attempts,
                "idempotency_key": e.idempotency_key,
                "next_retry_at": e.next_retry_at.isoformat() if e.next_retry_at else None,
                "created_at": e.created_at.isoformat() if e.created_at else None,
            }
            for e in events
        ],
    }


@router.post("/enqueue")
def enqueue(
    body: EnqueueBody,
    db: Session = Depends(get_db),
    facility_id: UUID = Depends(get_facility_context),
    user: User = Depends(require_permission("reports.read")),
):
    try:
        event = enqueue_event(
            db,
            facility_id=facility_id,
            event_type=body.event_type,
            payload=body.payload,
            idempotency_key=body.idempotency_key,
            actor_user_id=user.id,
        )
        db.commit()
        return {
            "id": str(event.id),
            "status": event.status,
            "event_type": event.event_type,
            "idempotency_key": event.idempotency_key,
        }
    except OfflineError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/drain")
def drain(
    db: Session = Depends(get_db),
    facility_id: UUID = Depends(get_facility_context),
    user: User = Depends(require_permission("reports.read")),
    limit: int = 25,
):
    result = drain_outbox(
        db, facility_id=facility_id, limit=limit, actor_user_id=user.id
    )
    db.commit()
    return result


@router.post("/connectivity-probe")
def connectivity_probe(
    body: ProbeBody,
    db: Session = Depends(get_db),
    facility_id: UUID = Depends(get_facility_context),
    user: User = Depends(require_permission("reports.read")),
):
    _ = user
    probe = record_connectivity_probe(
        db,
        facility_id=facility_id,
        target=body.target,
        ok=body.ok,
        latency_ms=body.latency_ms,
        detail=body.detail,
    )
    db.commit()
    return {
        "id": str(probe.id),
        "ok": probe.ok,
        "target": probe.target,
        "latency_ms": probe.latency_ms,
    }
