from __future__ import annotations

import hashlib
import logging
import os
import threading
import time
from urllib.parse import urljoin

import httpx
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.facilities.models import Facility

logger = logging.getLogger("afyasync.facilities.kmhfr")

SYNC_LOCK_KEY = "afyasync:kmhfr:facility-registry"
DEFAULT_KMHFR_URL = "https://api.kmhfr.health.go.ke/api/public/facilities/"
MAX_PAGES = 1000
PAGE_SIZE = 100
REQUEST_TIMEOUT = httpx.Timeout(connect=20.0, read=90.0, write=30.0, pool=20.0)
_sync_thread_lock = threading.Lock()
_sync_running = False
_last_sync_result: dict[str, int | str | bool] = {
    "running": False,
    "pages": 0,
    "seen": 0,
    "changed": 0,
    "message": "not_started",
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
    status = (_value(item, "operation_status_name", "operation_status", "status") or "Operational").strip().lower()
    return status in {"operational", "active", "open", "operating"}


def _stable_facility_id(key: str) -> str:
    return "KMHFR-" + hashlib.sha256(key.encode("utf-8")).hexdigest()[:25]


def _upsert(item: dict, db: Session) -> bool:
    code = _value(item, "code", "mfl_code", "facility_code", "facility_code_number")
    external_id = _value(item, "id", "uuid", "facility_id")
    name = _value(item, "name", "facility_official_name", "official_name")
    if not name:
        return False

    registry_key = code or external_id
    county = _value(item, "county_name", "county")
    sub_county = _value(item, "sub_county_name", "sub_county", "subcounty")
    facility_type = _value(item, "facility_type_name", "facility_type", "type") or "HEALTH_FACILITY"
    is_active = _active(item)

    facility = None
    if registry_key:
        facility = db.scalar(select(Facility).where(Facility.registration_number == registry_key).limit(1))
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


def _normalise_endpoint(value: str) -> str:
    value = value.strip()
    if not value:
        return DEFAULT_KMHFR_URL
    if value.endswith("/facilities"):
        return value + "/"
    if value.endswith("/facilities/"):
        return value
    if value.endswith("/api/public"):
        return value + "/facilities/"
    if value.endswith("/api/public/"):
        return value + "facilities/"
    return value.rstrip("/") + "/facilities/"


def _fetch_page(client: httpx.Client, url: str, page: int) -> tuple[dict | list, str | None]:
    last_error: Exception | None = None
    for attempt in range(1, 6):
        try:
            params = {"page_size": PAGE_SIZE, "page": page}
            response = client.get(url, params=params)
            response.raise_for_status()
            payload = response.json()
            if not isinstance(payload, (dict, list)):
                raise ValueError("KMHFR_INVALID_PAYLOAD")
            if isinstance(payload, dict):
                next_url = payload.get("next")
                if isinstance(next_url, str) and next_url:
                    return payload, next_url
            return payload, None
        except (httpx.TimeoutException, httpx.NetworkError, httpx.HTTPStatusError, ValueError) as exc:
            last_error = exc
            if attempt == 5:
                break
            delay = min(2 ** (attempt - 1), 12)
            logger.warning("KMHFR request failed page=%s attempt=%s/5 error=%s; retrying in %ss", page, attempt, exc, delay)
            time.sleep(delay)
    raise RuntimeError(f"KMHFR_REQUEST_FAILED page={page}: {last_error}") from last_error


def sync_all(*, force: bool = False) -> dict[str, int | str | bool]:
    global _sync_running, _last_sync_result
    db = SessionLocal()
    pages = 0
    changed = 0
    seen = 0
    try:
        if not _advisory_lock(db):
            result = {"running": True, "pages": 0, "seen": 0, "changed": 0, "message": "A national facility sync is already running."}
            _last_sync_result = result
            return result

        endpoint = _normalise_endpoint(os.getenv("KMHFR_API_BASE_URL", DEFAULT_KMHFR_URL))
        token = os.getenv("KMHFR_API_TOKEN", "").strip()
        headers = {
            "Accept": "application/json",
            "User-Agent": "AfyaSync/1.0 national-facility-sync",
        }
        if token:
            headers["Authorization"] = f"Bearer {token}"

        logger.info("Starting KMHFR national facility sync endpoint=%s", endpoint)
        with httpx.Client(timeout=REQUEST_TIMEOUT, follow_redirects=True, headers=headers) as client:
            url: str | None = endpoint
            page = 1
            while url and page <= MAX_PAGES:
                payload, next_url = _fetch_page(client, url, page)
                results = payload.get("results", []) if isinstance(payload, dict) else payload
                if not isinstance(results, list):
                    raise ValueError("KMHFR_INVALID_RESULTS")

                for item in results:
                    if isinstance(item, dict):
                        seen += 1
                        if _upsert(item, db):
                            changed += 1

                db.commit()
                pages += 1

                if isinstance(payload, dict):
                    total_pages = payload.get("total_pages")
                    total_count = payload.get("count")
                    if page == 1:
                        logger.info("KMHFR registry reports count=%s total_pages=%s", total_count, total_pages)
                    if next_url:
                        url = urljoin(url, next_url)
                    elif total_pages and page < int(total_pages):
                        page += 1
                        url = endpoint
                    else:
                        url = None
                else:
                    url = None

                if url and url == endpoint:
                    # Some KMHFR deployments expose page-based pagination without a next URL.
                    pass
                elif url:
                    page += 1
                else:
                    page += 1

                if pages % 10 == 0:
                    logger.info("KMHFR sync progress pages=%s seen=%s changed=%s", pages, seen, changed)

        result = {"running": False, "pages": pages, "seen": seen, "changed": changed, "message": "complete"}
        _last_sync_result = result
        logger.info("KMHFR national facility sync complete pages=%s seen=%s changed=%s", pages, seen, changed)
        return result
    except Exception:
        db.rollback()
        result = {"running": False, "pages": pages, "seen": seen, "changed": changed, "message": "failed"}
        _last_sync_result = result
        logger.exception("KMHFR national facility sync failed pages=%s seen=%s changed=%s", pages, seen, changed)
        return result
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


def sync_state(db: Session) -> dict[str, int | bool | str]:
    count = db.scalar(select(func.count(Facility.id)).where(Facility.status == "ACTIVE")) or 0
    return {
        "active_facilities": int(count),
        "sync_running": _sync_running,
        "pages": int(_last_sync_result.get("pages", 0)),
        "seen": int(_last_sync_result.get("seen", 0)),
        "changed": int(_last_sync_result.get("changed", 0)),
        "message": str(_last_sync_result.get("message", "not_started")),
    }
