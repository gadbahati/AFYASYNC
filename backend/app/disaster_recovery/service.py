"""DR checklist, backup verification records, drill lifecycle."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.audit.service import record_audit
from app.disaster_recovery.models import BackupVerification, DisasterRecoveryDrill

DRILL_TYPES = {"TABLETOP", "FAILOVER_SIM", "RESTORE_TEST"}
DRILL_STATUSES = {"PLANNED", "IN_PROGRESS", "PASSED", "FAILED", "CANCELLED"}
BACKUP_SOURCES = {"POSTGRES", "OBJECT_STORE", "WAL"}
BACKUP_STATUSES = {"RECORDED", "VERIFIED", "FAILED"}


class DRError(ValueError):
    pass


def dr_checklist() -> dict:
    return {
        "title": "AfyaSync disaster recovery checklist",
        "targets": {
            "rto_minutes_guidance": 240,
            "rpo_minutes_guidance": 60,
            "note": "Targets are policy guidance — tune per MoH SLA",
        },
        "steps": [
            {"id": "DR-01", "step": "Confirm daily Postgres backups and retention window"},
            {"id": "DR-02", "step": "Record last successful restore test via /api/v1/dr/backups"},
            {"id": "DR-03", "step": "Document WAL / PITR availability"},
            {"id": "DR-04", "step": "Run tabletop drill quarterly"},
            {"id": "DR-05", "step": "Verify /ready and /api/v1/production/readiness after restore"},
            {"id": "DR-06", "step": "Confirm secrets rotation path if host compromise"},
            {"id": "DR-07", "step": "Offline outbox catch-up after connectivity restored"},
        ],
        "developer": "BAHATI GAD WANGWE",
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def live_db_probe(db: Session) -> dict:
    """Lightweight connectivity probe — not a full restore."""
    t0 = datetime.now(timezone.utc)
    try:
        db.execute(text("SELECT 1"))
        ok = True
        detail = "SELECT 1 succeeded"
    except Exception as exc:
        ok = False
        detail = type(exc).__name__
    elapsed_ms = int((datetime.now(timezone.utc) - t0).total_seconds() * 1000)
    return {
        "ok": ok,
        "elapsed_ms": elapsed_ms,
        "detail": detail,
        "note": "Live probe only — does not prove backup restorability",
    }


def record_backup(
    db: Session,
    *,
    source: str = "POSTGRES",
    status: str = "RECORDED",
    detail: str | None = None,
    actor_user_id: UUID | None = None,
) -> BackupVerification:
    src = (source or "POSTGRES").strip().upper()
    st = (status or "RECORDED").strip().upper()
    if src not in BACKUP_SOURCES:
        raise DRError("INVALID_BACKUP_SOURCE")
    if st not in BACKUP_STATUSES:
        raise DRError("INVALID_BACKUP_STATUS")

    row = BackupVerification(
        source=src,
        status=st,
        detail=(detail or "").strip()[:2000] or None,
        recorded_by_user_id=actor_user_id,
    )
    db.add(row)
    db.flush()
    record_audit(
        db,
        action="BACKUP_VERIFICATION_RECORD",
        resource_type="BACKUP_VERIFICATION",
        resource_id=str(row.id),
        result=st,
        user_id=actor_user_id,
        metadata={"source": src},
        commit=False,
    )
    return row


def list_backups(db: Session, *, limit: int = 20) -> list[dict]:
    limit = max(1, min(limit, 100))
    rows = db.scalars(
        select(BackupVerification).order_by(BackupVerification.created_at.desc()).limit(limit)
    ).all()
    return [
        {
            "id": str(r.id),
            "source": r.source,
            "status": r.status,
            "detail": r.detail,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]


def start_drill(
    db: Session,
    *,
    drill_type: str,
    scenario: str,
    rto_minutes_target: int | None = None,
    rpo_minutes_target: int | None = None,
    actor_user_id: UUID | None = None,
) -> DisasterRecoveryDrill:
    dt = (drill_type or "TABLETOP").strip().upper()
    if dt not in DRILL_TYPES:
        raise DRError("INVALID_DRILL_TYPE")
    sc = scenario.strip()
    if len(sc) < 5:
        raise DRError("SCENARIO_REQUIRED")

    row = DisasterRecoveryDrill(
        drill_type=dt,
        status="PLANNED",
        scenario=sc[:500],
        rto_minutes_target=rto_minutes_target,
        rpo_minutes_target=rpo_minutes_target,
        conducted_by_user_id=actor_user_id,
    )
    db.add(row)
    db.flush()
    record_audit(
        db,
        action="DR_DRILL_START",
        resource_type="DR_DRILL",
        resource_id=str(row.id),
        result="PLANNED",
        user_id=actor_user_id,
        metadata={"drill_type": dt},
        commit=False,
    )
    return row


def complete_drill(
    db: Session,
    *,
    drill_id: UUID,
    status: str,
    outcome_notes: str | None = None,
    actor_user_id: UUID | None = None,
) -> DisasterRecoveryDrill:
    row = db.get(DisasterRecoveryDrill, drill_id)
    if row is None:
        raise DRError("DRILL_NOT_FOUND")
    st = status.strip().upper()
    if st not in DRILL_STATUSES:
        raise DRError("INVALID_DRILL_STATUS")
    if st == "PLANNED":
        raise DRError("CANNOT_COMPLETE_AS_PLANNED")

    row.status = st
    if outcome_notes is not None:
        row.outcome_notes = outcome_notes.strip()[:2000] or None
    if st in {"PASSED", "FAILED", "CANCELLED"}:
        row.completed_at = datetime.now(timezone.utc)
    row.conducted_by_user_id = actor_user_id or row.conducted_by_user_id
    db.flush()
    record_audit(
        db,
        action="DR_DRILL_COMPLETE",
        resource_type="DR_DRILL",
        resource_id=str(row.id),
        result=st,
        user_id=actor_user_id,
        commit=False,
    )
    return row


def list_drills(db: Session, *, limit: int = 20) -> list[dict]:
    limit = max(1, min(limit, 100))
    rows = db.scalars(
        select(DisasterRecoveryDrill).order_by(DisasterRecoveryDrill.created_at.desc()).limit(limit)
    ).all()
    return [
        {
            "id": str(r.id),
            "drill_type": r.drill_type,
            "status": r.status,
            "scenario": r.scenario,
            "outcome_notes": r.outcome_notes,
            "rto_minutes_target": r.rto_minutes_target,
            "rpo_minutes_target": r.rpo_minutes_target,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "completed_at": r.completed_at.isoformat() if r.completed_at else None,
        }
        for r in rows
    ]


def posture(db: Session) -> dict:
    backup_count = db.scalar(select(func.count()).select_from(BackupVerification)) or 0
    last_backup = db.scalar(
        select(BackupVerification).order_by(BackupVerification.created_at.desc()).limit(1)
    )
    drill_count = db.scalar(select(func.count()).select_from(DisasterRecoveryDrill)) or 0
    last_passed = db.scalar(
        select(DisasterRecoveryDrill)
        .where(DisasterRecoveryDrill.status == "PASSED")
        .order_by(DisasterRecoveryDrill.completed_at.desc())
        .limit(1)
    )
    probe = live_db_probe(db)

    score = 0.0
    if probe["ok"]:
        score += 30
    if backup_count > 0:
        score += 30
    if last_backup and last_backup.status == "VERIFIED":
        score += 20
    if last_passed is not None:
        score += 20

    band = "GREEN" if score >= 80 else ("AMBER" if score >= 50 else "RED")
    return {
        "band": band,
        "score": score,
        "db_probe": probe,
        "backup_records": int(backup_count),
        "last_backup_status": last_backup.status if last_backup else None,
        "drill_records": int(drill_count),
        "last_passed_drill_id": str(last_passed.id) if last_passed else None,
        "checklist": dr_checklist()["steps"],
        "developer": "BAHATI GAD WANGWE",
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
