"""Offline outbox service — enqueue, drain, connectivity."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.audit.service import record_audit
from app.encounters.service import create_encounter
from app.offline.models import OfflineConnectivityProbe, OfflineOutboxEvent

_log = logging.getLogger("afyasync.offline")

ALLOWED_EVENT_TYPES = {
    "CLAIM_SUBMIT",
    "ELIGIBILITY_CHECK",
    "HIE_EXPORT",
    "PAYMENT_NOTIFY",
    "APPOINTMENT_SYNC",
    "CLINICAL_ENCOUNTER",
    "CUSTOM",
}

RETRY_DELAYS = (30, 60, 120, 300, 600, 1800, 3600, 7200)


class OfflineError(ValueError):
    pass


def enqueue_event(
    db: Session,
    *,
    facility_id: UUID,
    event_type: str,
    payload: dict,
    idempotency_key: str,
    actor_user_id: UUID | None = None,
    max_attempts: int = 8,
) -> OfflineOutboxEvent:
    event_type = event_type.strip().upper()
    if event_type not in ALLOWED_EVENT_TYPES:
        raise OfflineError("INVALID_EVENT_TYPE")
    key = idempotency_key.strip()[:120]
    if not key:
        raise OfflineError("IDEMPOTENCY_KEY_REQUIRED")
    if not isinstance(payload, dict):
        raise OfflineError("PAYLOAD_MUST_BE_OBJECT")

    existing = db.scalar(
        select(OfflineOutboxEvent).where(
            OfflineOutboxEvent.facility_id == facility_id,
            OfflineOutboxEvent.idempotency_key == key,
        )
    )
    if existing is not None:
        return existing

    event = OfflineOutboxEvent(
        facility_id=facility_id,
        event_type=event_type,
        payload=payload,
        idempotency_key=key,
        status="PENDING",
        attempts=0,
        max_attempts=max(1, min(max_attempts, 20)),
        next_retry_at=datetime.now(timezone.utc),
        created_by=actor_user_id,
    )
    db.add(event)
    db.flush()
    record_audit(
        db,
        action="OFFLINE_ENQUEUE",
        resource_type="OFFLINE_OUTBOX",
        resource_id=str(event.id),
        result="PENDING",
        user_id=actor_user_id,
        facility_id=facility_id,
        metadata={"event_type": event_type, "idempotency_key": key},
        commit=False,
    )
    return event


def list_pending(db: Session, *, facility_id: UUID, limit: int = 50) -> list[OfflineOutboxEvent]:
    limit = max(1, min(limit, 200))
    return list(
        db.scalars(
            select(OfflineOutboxEvent)
            .where(
                OfflineOutboxEvent.facility_id == facility_id,
                OfflineOutboxEvent.status.in_(["PENDING", "FAILED"]),
            )
            .order_by(OfflineOutboxEvent.created_at.asc())
            .limit(limit)
        )
    )


def outbox_stats(db: Session, *, facility_id: UUID) -> dict:
    rows = db.execute(
        select(OfflineOutboxEvent.status, func.count())
        .where(OfflineOutboxEvent.facility_id == facility_id)
        .group_by(OfflineOutboxEvent.status)
    ).all()
    by_status = {str(s): int(c) for s, c in rows}
    return {
        "facility_id": str(facility_id),
        "by_status": by_status,
        "pending": by_status.get("PENDING", 0) + by_status.get("FAILED", 0),
        "synced": by_status.get("SYNCED", 0),
        "dead": by_status.get("DEAD", 0),
        "developer": "BAHATI GAD WANGWE",
    }


def _process_one(db: Session, event: OfflineOutboxEvent) -> str:
    """Apply local drain rules. External systems are not faked.

    - CUSTOM / APPOINTMENT_SYNC: mark SYNCED (local acknowledgement)
    - CLAIM_SUBMIT / ELIGIBILITY / HIE / PAYMENT: mark as queued for online path
      without inventing payer acceptance
    """
    et = event.event_type
    if et in {"CUSTOM", "APPOINTMENT_SYNC"}:
        return "SYNCED"
    if et == "CLINICAL_ENCOUNTER":
        required = {"patient_id", "department_id", "encounter_type"}
        if not required.issubset(event.payload):
            return "FAILED"
        try:
            payload = dict(event.payload)
            payload["facility_id"] = event.facility_id
            payload["patient_id"] = UUID(str(payload["patient_id"]))
            payload["department_id"] = UUID(str(payload["department_id"]))
            payload.pop("id", None)
            payload.pop("status", None)
            payload.pop("started_at", None)
            actor = event.created_by
            if actor is None:
                return "FAILED"
            create_encounter(db, payload, created_by=actor, actor_user_id=actor, commit=False)
            return "SYNCED"
        except (ValueError, TypeError, KeyError):
            return "FAILED"
    # External-bound events: accepted into outbox drain only if payload is well-formed.
    if not event.payload:
        return "FAILED"
    # Require a target reference so staff know what will go out when online
    if et == "CLAIM_SUBMIT" and not event.payload.get("claim_id"):
        return "FAILED"
    if et == "ELIGIBILITY_CHECK" and not event.payload.get("membership_number"):
        return "FAILED"
    if et == "HIE_EXPORT" and not event.payload.get("person_id"):
        return "FAILED"
    # Mark SYNCED means "accepted for online relay queue" — not SHA paid
    return "SYNCED"


def drain_outbox(
    db: Session,
    *,
    facility_id: UUID,
    limit: int = 25,
    actor_user_id: UUID | None = None,
) -> dict:
    now = datetime.now(timezone.utc)
    events = list(
        db.scalars(
            select(OfflineOutboxEvent)
            .where(
                OfflineOutboxEvent.facility_id == facility_id,
                OfflineOutboxEvent.status.in_(["PENDING", "FAILED"]),
            )
            .order_by(OfflineOutboxEvent.created_at.asc())
            .limit(max(1, min(limit, 100)))
            .with_for_update(skip_locked=True)
        )
    )
    results = []
    for event in events:
        if event.next_retry_at and event.next_retry_at > now:
            results.append({"id": str(event.id), "skipped": "NOT_DUE"})
            continue
        event.status = "PROCESSING"
        event.attempts += 1
        db.flush()
        try:
            outcome = _process_one(db, event)
            if outcome == "SYNCED":
                event.status = "SYNCED"
                event.synced_at = now
                event.last_error = None
                event.next_retry_at = None
            else:
                event.status = "FAILED"
                event.last_error = "VALIDATION_FAILED"
                delay = RETRY_DELAYS[min(event.attempts - 1, len(RETRY_DELAYS) - 1)]
                event.next_retry_at = now + timedelta(seconds=delay)
                if event.attempts >= event.max_attempts:
                    event.status = "DEAD"
        except Exception as exc:
            _log.error("offline_drain_failed id=%s err=%s", event.id, exc)
            event.status = "FAILED"
            event.last_error = str(exc)[:300]
            delay = RETRY_DELAYS[min(event.attempts - 1, len(RETRY_DELAYS) - 1)]
            event.next_retry_at = now + timedelta(seconds=delay)
            if event.attempts >= event.max_attempts:
                event.status = "DEAD"
        results.append({"id": str(event.id), "status": event.status, "attempts": event.attempts})

    record_audit(
        db,
        action="OFFLINE_DRAIN",
        resource_type="OFFLINE_OUTBOX",
        resource_id=str(facility_id),
        result="OK",
        user_id=actor_user_id,
        facility_id=facility_id,
        metadata={"processed": len(results)},
        commit=False,
    )
    return {"processed": len(results), "results": results, "developer": "BAHATI GAD WANGWE"}


def record_connectivity_probe(
    db: Session,
    *,
    facility_id: UUID | None,
    target: str,
    ok: bool,
    latency_ms: int | None = None,
    detail: str | None = None,
) -> OfflineConnectivityProbe:
    probe = OfflineConnectivityProbe(
        facility_id=facility_id,
        target=target[:200],
        ok=ok,
        latency_ms=latency_ms,
        detail=(detail or "")[:300] or None,
    )
    db.add(probe)
    db.flush()
    return probe
