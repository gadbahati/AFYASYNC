from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import logging
import os
import threading

import httpx
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.facilities.models import Facility

logger = logging.getLogger("afyasync.facilities.kmhfr")

SYNC_LOCK_KEY = "afyasync:kmhfr:facility-registry"
_sync_thread_lock = threading.Lock()
_sync_running = False


def _value(item: dict, *keys: str) -> str | None:
    for key in keys:
        value = item.get(key)
        if isinstance(value, dict):
            value = value.get("name") or value.get("label") or value.get("value") or value.get("code")
        if value is not None and str(value).strip():
            return str(value).strip()
    return None


def _active(item: dict) -> bool:
    status = (_value(item, "operation_status_name", "operation_status", "status") or "Operational").strip().lower()
    return status in {"operational", "active", "open", "operating"}


def _stable_facility_id(key: str) -> str:
    # Keep the external registry identity deterministic and within the model's 32-char limit.
    return "KMHFR-" + hashlib.sha256(key.encode("utf-8")).hexdigest()[:25]


def _upsert(item: dict, db: Session) -> bool:
    code = _value(item, "code", "mfl_code", "facility_code", "facility_code_number")
    external_id = _value(item, "id", "uuid")
    name = _value(item, "name", "facility_official_name", "official_name")
    if not name:
        return False

    registry_key = code or external_id
    county = _value(item, "county", "county_name")
    sub_county = _value(item, "sub_county", "subcounty", "sub_county_name")
    facility_type = _value(item, "facility_type_name", "facility_type", "type") or "HEALTH_FACILITY"
    is_active = _active(item)

    facility = None
    if registry_key:
        facility = db.scalar(
            select(Facility).where(Facility.registration_number == registry_key).limit(1)
        )
    if facility is None:
        facility = db.scalar(
            select(Facility).where(
                func.lower(Facility.name) == name.lower(),
                func.lower(func.coalesce(Facility.county, "")) == (county or "").lower(),
            ).limit(1)
        )

    if facility is None:
        identity = registry_key or f"{name}|{county or ''}|{sub_county or ''}"
        facility = Facility(
            facility_id=_stable_facility_id(identity),
            name=name,
            facility_type=facility_type,
            registration_number=registry_key,
            county=county,
            sub_county=sub_county,
            status="ACTIVE" if is_active else "INACTIVE",
        )
        db.add(facility)
        return True

    changed = False
    values = {
        "name": name,
        "facility_type": facility_type,
        "county": county,
        "sub_county": sub_county,
        "status": "ACTIVE" if is_active else "INACTIVE",
    }
    if registry_key:
        values["registration_number"] = registry_key
    for field, value in values.items():
        if value is not None and getattr(facility, field) != value:
            setattr(facility, field, value)
            changed = True
    return changed


def _advisory_lock(db: Session) -> bool:
    result = db.execute(
        text("SELECT pg_try_advisory_lock(hashtextextended(:key, 0))"),
        {"key": SYNC_LOCK_KEY},
    )
    return bool(result.scalar())


def _advisory_unlock(db: Session) -> None:
    db.execute(
        text("SELECT pg_advisory_unlock(hashtextextended(:key, 0))"),
        {"key": SYNC_LOCK_KEY},
    )


def sync_all(*, force: bool = False) -> dict[str, int | str | bool]:
    global _sync_running
    db = SessionLocal()
    pages = 0
    changed = 0
    seen = 0
    try:
        if not _advisory_lock(db):
            return {"running": True, "pages": 0, "seen": 0, "changed": 0, "message": "A national facility sync is already running."}

        base = os.getenv("KMHFR_API_BASE_URL", "https://api.kmhfr.health.go.ke/api").rstrip("/")
        url = f"{base}/facilities/facilities/"
        token = os.getenv("KMHFR_API_TOKEN", "").strip()
        headers = {"Accept": "application/json", "User-Agent": "AfyaSync/1.0 national-facility-sync"}
        if token:
            headers["Authorization"] = f"Bearer {token}"

        logger.info("Starting KMHFR national facility sync url=%s", url)
        with httpx.Client(timeout=45.0, follow_redirects=True, headers=headers) as client:
            while url:
                response = client.get(url, params={"page_size": 100} if pages == 0 else None)
                response.raise_for_status()
                payload = response.json()
                results = payload.get("results", payload if isinstance(payload, list) else [])
                if not isinstance(results, list):
                    raise ValueError("KMHFR_INVALID_RESULTS")
                for item in results:
                    if isinstance(item, dict):
                        seen += 1
                        if _upsert(item, db):
                            changed += 1
                db.commit()
                pages += 1
                next_url = payload.get("next") if isinstance(payload, dict) else None
                url = next_url if isinstance(next_url, str) and next_url else ""
                if pages % 10 == 0:
                    logger.info("KMHFR sync progress pages=%s seen=%s changed=%s", pages, seen, changed)

        logger.info("KMHFR national facility sync complete pages=%s seen=%s changed=%s", pages, seen, changed)
        return {"running": False, "pages": pages, "seen": seen, "changed": changed, "message": "complete"}
    except Exception:
        db.rollback()
        logger.exception("KMHFR national facility sync failed pages=%s seen=%s changed=%s", pages, seen, changed)
        return {"running": False, "pages": pages, "seen": seen, "changed": changed, "message": "failed"}
    finally:
        try:
            _advisory_unlock(db)
        except Exception:
            pass
        db.close()


def start_sync() -> bool:
    global _sync_running
    with _sync_thread_lock:
        if _sync_running:
            return False
        _sync_running = True

    def worker() -> None:
        global _sync_running
        try:
            sync_all()
        finally:
            with _sync_thread_lock:
                _sync_running = False

    threading.Thread(target=worker, name="kmhfr-national-sync", daemon=True).start()
    return True


def sync_state(db: Session) -> dict[str, int | bool]:
    count = db.scalar(select(func.count(Facility.id)).where(Facility.status == "ACTIVE")) or 0
    return {"active_facilities": int(count), "sync_running": _sync_running}
