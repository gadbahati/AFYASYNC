from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.audit.models import AuditLog
from app.facilities.models import Facility, FacilityRegistryRecord
from app.facilities.kmhfr_registry import sync_state
from app.patients.models import Person

SNAPSHOT = Path(__file__).resolve().parents[2] / "data" / "kmhfr_facilities.json"


def _safe_count(db: Session, statement) -> int:
    try:
        return int(db.scalar(statement) or 0)
    except Exception:
        db.rollback()
        return 0


def system_snapshot(db: Session) -> dict:
    now = datetime.now(timezone.utc)
    since = now - timedelta(hours=24)

    db_ok = True
    try:
        db.execute(text("SELECT 1"))
    except Exception:
        db_ok = False
        db.rollback()

    active_facilities = _safe_count(db, select(func.count(Facility.id)).where(Facility.status == "ACTIVE"))
    total_facilities = _safe_count(db, select(func.count(Facility.id)))
    registry_records = _safe_count(db, select(func.count(FacilityRegistryRecord.id)))
    patients = _safe_count(db, select(func.count(Person.id)))
    audit_24h = _safe_count(db, select(func.count(AuditLog.id)).where(AuditLog.created_at >= since))
    audit_errors_24h = _safe_count(db, select(func.count(AuditLog.id)).where(AuditLog.created_at >= since, AuditLog.result != "SUCCESS"))

    snapshot_exists = SNAPSHOT.exists()
    snapshot_records = 0
    snapshot_generated_at = None
    snapshot_api_count = 0
    if snapshot_exists:
        try:
            import json
            payload = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
            records = payload.get("records", []) if isinstance(payload, dict) else []
            snapshot_records = len(records) if isinstance(records, list) else 0
            snapshot_generated_at = payload.get("generated_at") if isinstance(payload, dict) else None
            snapshot_api_count = int(payload.get("api_count") or 0) if isinstance(payload, dict) else 0
        except Exception:
            snapshot_exists = False

    return {
        "timestamp": now,
        "database": {"status": "ok" if db_ok else "unavailable"},
        "facilities": {
            "active": active_facilities,
            "total": total_facilities,
            "registry_records": registry_records,
        },
        "patients": {"total": patients},
        "audit": {"events_24h": audit_24h, "non_success_24h": audit_errors_24h},
        "kmhfr": {
            "snapshot_available": snapshot_exists,
            "snapshot_records": snapshot_records,
            "snapshot_api_count": snapshot_api_count,
            "snapshot_generated_at": snapshot_generated_at,
            "registry": sync_state(db),
        },
    }
