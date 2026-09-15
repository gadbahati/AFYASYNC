from __future__ import annotations

import hashlib
import json
import logging
import threading
import time
from pathlib import Path

from sqlalchemy import func, select, text

from app.database import SessionLocal
from app.facilities.models import Facility

logger = logging.getLogger("afyasync.facilities.kmhfr")
LOCK_KEY = "afyasync:kmhfr:facility-registry"
SNAPSHOT = Path(__file__).resolve().parents[2] / "data" / "kmhfr_facilities.json"
MIN_SNAPSHOT_RECORDS = 10_000
TARGET_ACTIVE_FACILITIES = 10_000
_lock = threading.Lock()
_running = False
_retry_started = False
_state: dict[str, int | bool | str] = {
    "running": False,
    "pages": 0,
    "seen": 0,
    "changed": 0,
    "message": "not_started",
    "source": "none",
}


def _value(item: dict, *keys: str) -> str | None:
    for key in keys:
        value = item.get(key)
        if isinstance(value, dict):
            value = value.get("name") or value.get("label") or value.get("value") or value.get("code")
        if value is not None and str(value).strip():
            return str(value).strip()
    return None


def _active(item: dict) -> bool:
    return (_value(item, "operation_status", "operation_status_name", "status") or "Operational").lower() in {
        "operational", "active", "open", "operating"
    }


def _facility_id(key: str) -> str:
    return "KMHFR-" + hashlib.sha256(key.encode()).hexdigest()[:25]


def _upsert(db, item: dict) -> bool:
    code = _value(item, "code", "mfl_code", "facility_code", "facility_code_number")
    external = _value(item, "id", "uuid", "facility_id")
    name = _value(item, "name", "facility_official_name", "official_name")
    if not name:
        return False
    key = code or external or f"{name}|{_value(item, 'county_name', 'county') or ''}|{_value(item, 'sub_county_name', 'sub_county', 'subcounty') or ''}"
    county = _value(item, "county_name", "county")
    sub_county = _value(item, "sub_county_name", "sub_county", "subcounty")
    kind = _value(item, "facility_type_name", "facility_type", "type") or "HEALTH_FACILITY"
    registration = code or external

    existing = db.scalar(select(Facility).where(Facility.registration_number == registration).limit(1)) if registration else None
    if existing is None:
        existing = db.scalar(
            select(Facility)
            .where(
                func.lower(Facility.name) == name.lower(),
                func.lower(func.coalesce(Facility.county, "")) == (county or "").lower(),
            )
            .limit(1)
        )

    if existing is None:
        db.add(
            Facility(
                facility_id=_facility_id(key),
                name=name,
                facility_type=kind,
                registration_number=registration,
                county=county,
                sub_county=sub_county,
                status="ACTIVE" if _active(item) else "INACTIVE",
            )
        )
        return True

    changed = False
    values = {
        "name": name,
        "facility_type": kind,
        "county": county,
        "sub_county": sub_county,
        "status": "ACTIVE" if _active(item) else "INACTIVE",
    }
    if registration:
        values["registration_number"] = registration
    for field, value in values.items():
        if value is not None and getattr(existing, field) != value:
            setattr(existing, field, value)
            changed = True
    return changed


def _live_sync() -> dict[str, int | bool | str]:
    """Use the live official KMHFR API when a GitHub snapshot is unavailable."""
    from app.facilities.kmhfr_sync import sync_all as sync_live

    result = sync_live(force=True)
    return {
        "running": bool(result.get("running", False)),
        "pages": int(result.get("pages", 0)),
        "seen": int(result.get("seen", 0)),
        "changed": int(result.get("changed", 0)),
        "message": str(result.get("message", "unknown")),
        "source": "official_kmhfr_api",
    }


def sync_all(*, force: bool = False) -> dict[str, int | bool | str]:
    global _state
    db = SessionLocal()
    seen = changed = 0
    locked = False
    try:
        if not SNAPSHOT.exists():
            logger.warning("KMHFR snapshot unavailable; falling back to live official KMHFR API")
            _state = _live_sync()
            return _state

        locked = bool(
            db.execute(
                text("SELECT pg_try_advisory_lock(hashtextextended(:key, 0))"),
                {"key": LOCK_KEY},
            ).scalar()
        )
        if not locked:
            return {"running": True, "pages": 0, "seen": 0, "changed": 0, "message": "already_running", "source": "snapshot"}

        with SNAPSHOT.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
        records = payload.get("records") if isinstance(payload, dict) else payload
        if not isinstance(records, list) or len(records) < MIN_SNAPSHOT_RECORDS:
            raise RuntimeError(f"KMHFR_SNAPSHOT_INVALID:{len(records) if isinstance(records, list) else 0}")

        logger.info("KMHFR_SNAPSHOT_IMPORT_START records=%s source=%s", len(records), payload.get("source") if isinstance(payload, dict) else "unknown")
        for item in records:
            if isinstance(item, dict):
                seen += 1
                if _upsert(db, item):
                    changed += 1
            if seen % 500 == 0:
                db.commit()
                if seen % 5000 == 0:
                    logger.info("KMHFR_SNAPSHOT_IMPORT_PROGRESS seen=%s changed=%s", seen, changed)
        db.commit()

        _state = {"running": False, "pages": 1, "seen": seen, "changed": changed, "message": "complete", "source": "official_kmhfr_snapshot"}
        logger.info("KMHFR_SNAPSHOT_IMPORT_COMPLETE seen=%s changed=%s", seen, changed)
        return _state
    except Exception as exc:
        db.rollback()
        _state = {"running": False, "pages": 0, "seen": seen, "changed": changed, "message": f"failed:{type(exc).__name__}", "source": "snapshot"}
        logger.exception("KMHFR_REGISTRY_IMPORT_FAILED seen=%s", seen)
        return _state
    finally:
        if locked:
            try:
                db.execute(text("SELECT pg_advisory_unlock(hashtextextended(:key, 0))"), {"key": LOCK_KEY})
            except Exception:
                pass
        db.close()


def start_sync() -> bool:
    global _running
    with _lock:
        if _running:
            return False
        _running = True

    def worker():
        global _running
        try:
            sync_all()
        finally:
            with _lock:
                _running = False

    threading.Thread(target=worker, name="kmhfr-registry-import", daemon=True).start()
    return True


def start_sync_retry_loop() -> bool:
    global _retry_started
    with _lock:
        if _retry_started:
            return False
        _retry_started = True

    def worker():
        time.sleep(10)
        while True:
            try:
                with SessionLocal() as db:
                    active = db.scalar(select(func.count(Facility.id)).where(Facility.status == "ACTIVE")) or 0
                if active >= TARGET_ACTIVE_FACILITIES:
                    logger.info("KMHFR_REGISTRY_READY active_facilities=%s", active)
                    return
                if not _running:
                    logger.info("KMHFR_REGISTRY_RETRY active_facilities=%s", active)
                    start_sync()
            except Exception:
                logger.exception("KMHFR_REGISTRY_RETRY_CHECK_FAILED")
            time.sleep(60)

    threading.Thread(target=worker, name="kmhfr-registry-retry", daemon=True).start()
    return True


def sync_state(db) -> dict[str, int | bool | str]:
    active = db.scalar(select(func.count(Facility.id)).where(Facility.status == "ACTIVE")) or 0
    total = db.scalar(select(func.count(Facility.id))) or 0
    return {"active_facilities": int(active), "total_facilities": int(total), "sync_running": _running, **_state}
