from __future__ import annotations

import hashlib
import json
import logging
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import func, select, text

from app.database import SessionLocal
from app.facilities.models import Facility, FacilityRegistryHistory, FacilityRegistryRecord

logger = logging.getLogger("afyasync.facilities.kmhfr")
LOCK_KEY = "afyasync:kmhfr:facility-registry"
SNAPSHOT = Path(__file__).resolve().parents[2] / "data" / "kmhfr_facilities.json"
MIN_SNAPSHOT_RECORDS = 10_000
TARGET_REGISTRY_RECORDS = 10_000
_lock = threading.Lock()
_running = False
_retry_started = False
_state: dict[str, int | bool | str] = {
    "running": False, "pages": 0, "seen": 0, "changed": 0,
    "message": "not_started", "source": "none", "last_success_at": ""
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
    return (_value(item, "operation_status", "operation_status_name", "status") or "Operational").lower() in {"operational", "active", "open", "operating"}


def _facility_id(key: str) -> str:
    return "KMHFR-" + hashlib.sha256(key.encode()).hexdigest()[:25]


def _number(item: dict, *keys: str) -> float | None:
    value = _value(item, *keys)
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _source_timestamp(item: dict) -> datetime | None:
    raw = _value(item, "updated_at", "updated", "last_updated", "date_updated", "modified_at")
    if not raw:
        return None
    try:
        normalized = raw.replace("Z", "+00:00")
        parsed = datetime.fromisoformat(normalized)
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def _record_values(item: dict) -> dict:
    return {
        "source_id": _value(item, "id", "uuid", "facility_id"),
        "mfl_code": _value(item, "code", "mfl_code", "facility_code", "facility_code_number"),
        "keph_level": _value(item, "keph_level", "keph_level_name", "level"),
        "ownership": _value(item, "owner_name", "owner", "ownership_name", "ownership"),
        "ward": _value(item, "ward_name", "ward"),
        "constituency": _value(item, "constituency_name", "constituency"),
        "address": _value(item, "address", "physical_address", "location"),
        "phone": _value(item, "phone", "telephone", "phone_number", "mobile"),
        "email": _value(item, "email", "email_address"),
        "latitude": _number(item, "latitude", "lat"),
        "longitude": _number(item, "longitude", "lng", "lon"),
        "services": item.get("services") if isinstance(item.get("services"), (list, dict)) else None,
        "source_updated_at": _source_timestamp(item),
    }


def _upsert(db, item: dict) -> bool:
    name = _value(item, "name", "facility_official_name", "official_name", "facility_unique_name")
    if not name:
        return False
    registry = _record_values(item)
    registration = registry["mfl_code"] or registry["source_id"]
    county = _value(item, "county_name", "county")
    sub_county = _value(item, "sub_county_name", "sub_county", "subcounty")
    kind = _value(item, "facility_type_name", "facility_type", "type") or "HEALTH_FACILITY"
    active = _active(item)

    facility = db.scalar(select(Facility).where(Facility.registration_number == registration).limit(1)) if registration else None
    if facility is None:
        facility = db.scalar(select(Facility).where(func.lower(Facility.name) == name.lower(), func.lower(func.coalesce(Facility.county, "")) == (county or "").lower()).limit(1))

    action = "UPDATED"
    if facility is None:
        identity = registration or f"{name}|{county or ''}|{sub_county or ''}"
        facility = Facility(facility_id=_facility_id(identity), name=name, facility_type=kind, registration_number=registration, county=county, sub_county=sub_county, status="ACTIVE" if active else "INACTIVE")
        db.add(facility)
        db.flush()
        action = "CREATED"
        before = None
    else:
        before = {"name": facility.name, "facility_type": facility.facility_type, "registration_number": facility.registration_number, "county": facility.county, "sub_county": facility.sub_county, "status": facility.status}
        changed = False
        for field, value in {"name": name, "facility_type": kind, "county": county, "sub_county": sub_county, "status": "ACTIVE" if active else "INACTIVE", "registration_number": registration}.items():
            if value is not None and getattr(facility, field) != value:
                setattr(facility, field, value)
                changed = True
        if not changed:
            action = "SEEN"

    existing = db.scalar(select(FacilityRegistryRecord).where(FacilityRegistryRecord.facility_id == facility.id).limit(1))
    now = datetime.now(timezone.utc)
    full_after = {"name": name, "facility_type": kind, "registration_number": registration, "county": county, "sub_county": sub_county, "status": "ACTIVE" if active else "INACTIVE", **registry}
    if existing is None:
        existing = FacilityRegistryRecord(facility_id=facility.id, source="KMHFR", **registry, raw_record=item, last_seen_at=now)
        db.add(existing)
        if action == "SEEN":
            action = "CREATED"
        changed_fields = sorted(full_after.keys())
    else:
        old = {column: getattr(existing, column) for column in registry}
        changed_fields = sorted(column for column in registry if old.get(column) != registry[column])
        if existing.raw_record != item:
            changed_fields.append("raw_record")
        for column, value in registry.items():
            setattr(existing, column, value)
        existing.raw_record = item
        existing.last_seen_at = now
        if changed_fields and action == "SEEN":
            action = "UPDATED"

    if action != "SEEN":
        db.add(FacilityRegistryHistory(facility_id=facility.id, source="KMHFR", action=action, changed_fields=changed_fields, before_record=before, after_record=full_after))
    return action != "SEEN"


def sync_all(*, force: bool = False) -> dict[str, int | bool | str]:
    global _state
    db = SessionLocal()
    seen = changed = 0
    locked = False
    try:
        locked = bool(db.execute(text("SELECT pg_try_advisory_lock(hashtextextended(:key, 0))"), {"key": LOCK_KEY}).scalar())
        if not locked:
            return {"running": True, "pages": 0, "seen": 0, "changed": 0, "message": "already_running", "source": "snapshot"}
        if not SNAPSHOT.exists():
            _state = {"running": False, "pages": 0, "seen": 0, "changed": 0, "message": "snapshot_unavailable", "source": "none", "last_success_at": str(_state.get("last_success_at", ""))}
            logger.warning("KMHFR_SNAPSHOT_UNAVAILABLE; national registry will remain on local data until the official snapshot is available")
            return _state
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
        timestamp = datetime.now(timezone.utc).isoformat()
        _state = {"running": False, "pages": 1, "seen": seen, "changed": changed, "message": "complete", "source": "official_kmhfr_snapshot", "last_success_at": timestamp}
        logger.info("KMHFR_SNAPSHOT_IMPORT_COMPLETE seen=%s changed=%s", seen, changed)
        return _state
    except Exception as exc:
        db.rollback()
        _state = {"running": False, "pages": 0, "seen": seen, "changed": changed, "message": f"failed:{type(exc).__name__}", "source": "snapshot", "last_success_at": str(_state.get("last_success_at", ""))}
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
    start_sync_retry_loop()
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
                    registry_records = db.scalar(select(func.count(FacilityRegistryRecord.id))) or 0
                if registry_records >= TARGET_REGISTRY_RECORDS:
                    logger.info("KMHFR_REGISTRY_READY registry_records=%s", registry_records)
                    return
                if not _running:
                    logger.info("KMHFR_REGISTRY_RETRY registry_records=%s", registry_records)
                    start_sync()
            except Exception:
                logger.exception("KMHFR_REGISTRY_RETRY_CHECK_FAILED")
            time.sleep(60)
    threading.Thread(target=worker, name="kmhfr-registry-retry", daemon=True).start()
    return True


def sync_state(db) -> dict[str, int | bool | str]:
    active = db.scalar(select(func.count(Facility.id)).where(Facility.status == "ACTIVE")) or 0
    total = db.scalar(select(func.count(Facility.id))) or 0
    registry = db.scalar(select(func.count(FacilityRegistryRecord.id))) or 0
    return {"active_facilities": int(active), "total_facilities": int(total), "registry_records": int(registry), "sync_running": _running, **_state}
