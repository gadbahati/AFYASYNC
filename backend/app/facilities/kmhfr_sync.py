from __future__ import annotations

import hashlib
import logging
import threading
import time
from math import ceil

import httpx
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.facilities.models import Facility

logger = logging.getLogger("afyasync.facilities.kmhfr")

SYNC_LOCK_KEY = "afyasync:kmhfr:facility-registry"
DEFAULT_KMHFR_URL = "https://api.kmhfr.health.go.ke/api/public/facilities/"
DIRECT_KMHFR_URL = "https://api.kmhfr.health.go.ke/api/facilities/facilities/"
MAX_PAGES = 1000
PAGE_SIZE = 100
REQUEST_TIMEOUT = httpx.Timeout(connect=60.0, read=180.0, write=30.0, pool=30.0)
RETRY_INTERVAL_SECONDS = 60
_sync_thread_lock = threading.Lock()
_sync_running = False
_retry_thread_started = False
_last_sync_result: dict[str, int | str | bool] = {"running": False, "pages": 0, "seen": 0, "changed": 0, "message": "not_started"}


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
    return "KMHFR-" + hashlib.sha256(key.encode("utf-8")).hexdigest()[:25]


def _upsert(item: dict, db: Session) -> bool:
    code = _value(item, "code", "mfl_code", "facility_code", "facility_code_number")
    external_id = _value(item, "id", "uuid", "facility_id")
    name = _value(item, "name", "facility_official_name", "official_name", "facility_unique_name")
    if not name:
        return False
    registry_key = code or external_id
    county = _value(item, "county_name", "county")
    sub_county = _value(item, "sub_county_name", "sub_county", "subcounty")
    facility_type = _value(item, "facility_type_name", "facility_type", "type") or "HEALTH_FACILITY"
    is_active = _active(item)
    facility = db.scalar(select(Facility).where(Facility.registration_number == registry_key).limit(1)) if registry_key else None
    if facility is None:
        facility = db.scalar(select(Facility).where(func.lower(Facility.name) == name.lower(), func.lower(func.coalesce(Facility.county, "")) == (county or "").lower()).limit(1))
    if facility is None:
        identity = registry_key or f"{name}|{county or ''}|{sub_county or ''}"
        db.add(Facility(facility_id=_stable_facility_id(identity), name=name, facility_type=facility_type, registration_number=registry_key, county=county, sub_county=sub_county, status="ACTIVE" if is_active else "INACTIVE"))
        return True
    changed = False
    values = {"name": name, "facility_type": facility_type, "county": county, "sub_county": sub_county, "status": "ACTIVE" if is_active else "INACTIVE"}
    if registry_key:
        values["registration_number"] = registry_key
    for field, value in values.items():
        if value is not None and getattr(facility, field) != value:
            setattr(facility, field, value)
            changed = True
    return changed


def _advisory_lock(db: Session) -> bool:
    return bool(db.execute(text("SELECT pg_try_advisory_lock(hashtextextended(:key, 0))"), {"key": SYNC_LOCK_KEY}).scalar())


def _advisory_unlock(db: Session) -> None:
    db.execute(text("SELECT pg_advisory_unlock(hashtextextended(:key, 0))"), {"key": SYNC_LOCK_KEY})


def _fetch_page(client: httpx.Client, page: int) -> tuple[dict | list, int | None, str]:
    candidates = [
        (DEFAULT_KMHFR_URL, "official_public_api"),
        (DIRECT_KMHFR_URL, "official_facilities_api"),
    ]
    last_error: Exception | None = None
    for endpoint, source in candidates:
        for attempt in range(1, 4):
            try:
                response = client.get(endpoint, params={"page_size": PAGE_SIZE, "page": page, "format": "json"})
                response.raise_for_status()
                payload = response.json()
                if not isinstance(payload, (dict, list)):
                    raise ValueError("KMHFR_INVALID_PAYLOAD")
                if isinstance(payload, dict):
                    count = payload.get("count")
                    total_pages = payload.get("total_pages")
                    if total_pages is None and isinstance(count, int):
                        total_pages = ceil(count / PAGE_SIZE)
                    logger.info("KMHFR_PAGE_SOURCE page=%s source=%s count=%s total_pages=%s", page, source, count, total_pages)
                    return payload, int(total_pages) if total_pages else None, source
                logger.info("KMHFR_PAGE_SOURCE page=%s source=%s", page, source)
                return payload, None, source
            except (httpx.TimeoutException, httpx.NetworkError, httpx.HTTPStatusError, ValueError) as exc:
                last_error = exc
                logger.warning("KMHFR_PAGE_ATTEMPT_FAILED page=%s source=%s attempt=%s error=%s", page, source, attempt, type(exc).__name__)
                if attempt < 3:
                    time.sleep(2 ** (attempt - 1))
    raise RuntimeError(f"KMHFR_REQUEST_FAILED page={page}: {last_error}") from last_error


def sync_all(*, force: bool = False) -> dict[str, int | str | bool]:
    global _last_sync_result
    db = SessionLocal()
    pages = changed = seen = 0
    locked = False
    try:
        locked = _advisory_lock(db)
        if not locked:
            result = {"running": True, "pages": 0, "seen": 0, "changed": 0, "message": "already_running"}
            _last_sync_result = result
            return result
        logger.info("KMHFR_SYNC_START page_size=%s force=%s", PAGE_SIZE, force)
        with httpx.Client(timeout=REQUEST_TIMEOUT, follow_redirects=True, headers={"Accept": "application/json", "User-Agent": "AfyaSync/1.0 national-facility-sync"}) as client:
            page = 1
            total_pages: int | None = None
            while page <= MAX_PAGES:
                payload, discovered_pages, source = _fetch_page(client, page)
                if discovered_pages:
                    total_pages = discovered_pages
                results = payload.get("results", []) if isinstance(payload, dict) else payload
                if not isinstance(results, list):
                    raise ValueError("KMHFR_INVALID_RESULTS")
                if not results:
                    break
                for item in results:
                    if isinstance(item, dict):
                        seen += 1
                        if _upsert(item, db):
                            changed += 1
                db.commit()
                pages += 1
                if pages % 10 == 0:
                    logger.info("KMHFR_SYNC_PROGRESS pages=%s seen=%s changed=%s total_pages=%s source=%s", pages, seen, changed, total_pages, source)
                if total_pages and page >= total_pages:
                    break
                if len(results) < PAGE_SIZE and not total_pages:
                    break
                page += 1
        result = {"running": False, "pages": pages, "seen": seen, "changed": changed, "message": "complete"}
        _last_sync_result = result
        logger.info("KMHFR_SYNC_COMPLETE pages=%s seen=%s changed=%s", pages, seen, changed)
        return result
    except Exception as exc:
        db.rollback()
        result = {"running": False, "pages": pages, "seen": seen, "changed": changed, "message": f"failed:{type(exc).__name__}"}
        _last_sync_result = result
        logger.exception("KMHFR_SYNC_FAILED pages=%s seen=%s changed=%s", pages, seen, changed)
        return result
    finally:
        if locked:
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


def start_sync_retry_loop() -> bool:
    global _retry_thread_started
    with _sync_thread_lock:
        if _retry_thread_started:
            return False
        _retry_thread_started = True
    def retry_worker() -> None:
        time.sleep(15)
        while True:
            try:
                with SessionLocal() as db:
                    active = db.scalar(select(func.count(Facility.id)).where(Facility.status == "ACTIVE")) or 0
                if active < 10000 and not _sync_running:
                    logger.info("KMHFR_SYNC_RETRY active_facilities=%s", active)
                    start_sync()
                elif active >= 10000:
                    logger.info("KMHFR_SYNC_READY active_facilities=%s", active)
                    return
            except Exception:
                logger.exception("KMHFR_SYNC_RETRY_CHECK_FAILED")
            time.sleep(RETRY_INTERVAL_SECONDS)
    threading.Thread(target=retry_worker, name="kmhfr-sync-retry", daemon=True).start()
    return True


def sync_state(db: Session) -> dict[str, int | bool | str]:
    active = db.scalar(select(func.count(Facility.id)).where(Facility.status == "ACTIVE")) or 0
    total = db.scalar(select(func.count(Facility.id))) or 0
    return {"active_facilities": int(active), "total_facilities": int(total), "sync_running": _sync_running, "pages": int(_last_sync_result.get("pages", 0)), "seen": int(_last_sync_result.get("seen", 0)), "changed": int(_last_sync_result.get("changed", 0)), "message": str(_last_sync_result.get("message", "not_started"))}
