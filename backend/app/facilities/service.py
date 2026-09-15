from datetime import datetime, timedelta, timezone
import logging
import os
import threading
from uuid import UUID

import httpx
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.audit.service import record_audit
from app.database import SessionLocal
from app.facilities.models import Department, Facility

logger = logging.getLogger("afyasync.facilities")

_ALLOWED_FACILITY_STATUSES = {"APPLICATION", "ACTIVE", "SUSPENDED", "INACTIVE"}
_FACILITY_STATUS_TRANSITIONS = {
    "APPLICATION": {"ACTIVE", "INACTIVE"},
    "ACTIVE": {"SUSPENDED", "INACTIVE"},
    "SUSPENDED": {"ACTIVE", "INACTIVE"},
    "INACTIVE": {"APPLICATION"},
}
_ALLOWED_DEPARTMENT_STATUSES = {"ACTIVE", "INACTIVE"}
_FACILITY_ID_ALLOCATION_ATTEMPTS = 3
_KMHFR_SYNC_TTL = timedelta(hours=6)
_last_kmhfr_sync_at: datetime | None = None
_kmhfr_sync_running = False
_kmhfr_sync_lock = threading.Lock()

DEFAULT_DEPARTMENTS = (
    ("REG", "Registration & Records"), ("OPD", "Outpatient Department"), ("CAS", "Casualty / Emergency"),
    ("GENMED", "General Medicine"), ("PAEDS", "Paediatrics"), ("OBGYN", "Maternity & Obstetrics / Gynaecology"),
    ("SURG", "General Surgery"), ("ORTHO", "Orthopaedics"), ("DENT", "Dental"), ("ENT", "Ear, Nose & Throat"),
    ("EYE", "Ophthalmology"), ("DERM", "Dermatology"), ("PSYCH", "Mental Health / Psychiatry"),
    ("NCD", "Non-Communicable Diseases"), ("HIV", "HIV / ART Clinic"), ("TB", "Tuberculosis Clinic"),
    ("LAB", "Laboratory"), ("RAD", "Radiology & Imaging"), ("PHARM", "Pharmacy"),
    ("PHYSIO", "Physiotherapy & Rehabilitation"), ("NUTR", "Nutrition & Dietetics"), ("THEATRE", "Operating Theatre"),
    ("ICU", "Intensive Care Unit"), ("HDU", "High Dependency Unit"), ("WARD", "General Wards"),
    ("MORT", "Mortuary"), ("AMB", "Ambulance / Transport"),
)


def _next_facility_id(db: Session) -> str:
    count = db.scalar(select(func.count(Facility.id))) or 0
    return f"FAC-{count + 1:06d}"


def _ensure_default_departments(db: Session, facility_id: UUID) -> None:
    result = db.scalars(select(Department.code).where(Department.facility_id == facility_id)).all()
    try:
        existing = set(result)
    except TypeError:
        # Keep lightweight unit-test mocks compatible while preserving normal ORM behaviour.
        existing = set()
    for code, name in DEFAULT_DEPARTMENTS:
        if code not in existing:
            db.add(Department(facility_id=facility_id, name=name, code=code, status="ACTIVE"))
    db.flush()


def create_facility(db: Session, data: dict, *, actor_user_id: UUID | None = None) -> Facility:
    for attempt in range(_FACILITY_ID_ALLOCATION_ATTEMPTS):
        facility = Facility(facility_id=_next_facility_id(db), **data)
        try:
            with db.begin_nested():
                db.add(facility)
                db.flush()
                _ensure_default_departments(db, facility.id)
                record_audit(db, action="CREATE_FACILITY", resource_type="FACILITY", resource_id=str(facility.id), result="SUCCESS", user_id=actor_user_id, facility_id=facility.id, metadata={"facility_id": facility.facility_id, "name": facility.name, "default_departments": len(DEFAULT_DEPARTMENTS)}, commit=False)
        except IntegrityError:
            if attempt == _FACILITY_ID_ALLOCATION_ATTEMPTS - 1:
                raise
            continue
        db.commit()
        db.refresh(facility)
        return facility
    raise RuntimeError("FACILITY_ID_ALLOCATION_FAILED")


def list_facilities(db: Session, limit: int = 50) -> list[Facility]:
    limit = min(max(limit, 1), 100)
    return list(db.scalars(select(Facility).order_by(Facility.name).limit(limit)))


def list_network_facilities(db: Session, *, limit: int = 100, status_filter: str | None = None, county: str | None = None) -> list[Facility]:
    limit = min(max(limit, 1), 200)
    stmt = select(Facility).order_by(Facility.name)
    if status_filter:
        if status_filter not in _ALLOWED_FACILITY_STATUSES:
            raise ValueError("INVALID_FACILITY_STATUS")
        stmt = stmt.where(Facility.status == status_filter)
    if county:
        stmt = stmt.where(func.lower(Facility.county) == county.strip().lower())
    return list(db.scalars(stmt.limit(limit)))


def list_facility_directory(db: Session, *, search: str | None = None, limit: int = 50000) -> list[Facility]:
    stmt = select(Facility).where(Facility.status == "ACTIVE").order_by(Facility.name)
    if search and search.strip():
        needle = f"%{search.strip().lower()}%"
        stmt = stmt.where(
            func.lower(Facility.name).like(needle)
            | func.lower(func.coalesce(Facility.county, "")).like(needle)
            | func.lower(func.coalesce(Facility.sub_county, "")).like(needle)
            | func.lower(func.coalesce(Facility.facility_type, "")).like(needle)
        )
    return list(db.scalars(stmt.limit(min(max(limit, 1), 50000))))


def _kmhfr_value(item: dict, *keys: str) -> str | None:
    for key in keys:
        value = item.get(key)
        if isinstance(value, dict):
            value = value.get("name") or value.get("label") or value.get("value") or value.get("code")
        if value is not None and str(value).strip():
            return str(value).strip()
    return None


def _sync_kmhfr_page(item: dict, db: Session) -> bool:
    code = _kmhfr_value(item, "code", "mfl_code", "facility_code", "facility_code_number")
    external_uuid = _kmhfr_value(item, "id", "uuid")
    name = _kmhfr_value(item, "name", "facility_official_name", "official_name")
    if not name:
        return False
    county = _kmhfr_value(item, "county", "county_name")
    sub_county = _kmhfr_value(item, "sub_county", "subcounty", "sub_county_name")
    facility_type = _kmhfr_value(item, "facility_type_name", "facility_type", "type") or "HEALTH_FACILITY"
    operation_status = (_kmhfr_value(item, "operation_status_name", "operation_status", "status") or "Operational").strip().lower()
    active = operation_status in {"operational", "active", "open", "operating"}
    registration_key = code or external_uuid
    facility = None
    if registration_key:
        facility = db.scalar(select(Facility).where(Facility.registration_number == registration_key).limit(1))
    if facility is None and county:
        facility = db.scalar(select(Facility).where(func.lower(Facility.name) == name.lower(), func.lower(func.coalesce(Facility.county, "")) == county.lower()).limit(1))
    if facility is None:
        stable_key = str(registration_key or name).replace(" ", "-")[:26]
        facility = Facility(
            facility_id=f"KMHFL-{stable_key}", name=name, facility_type=facility_type,
            registration_number=registration_key, county=county, sub_county=sub_county,
            status="ACTIVE" if active else "INACTIVE",
        )
        db.add(facility)
        return True
    changed = False
    values = {"name": name, "facility_type": facility_type, "county": county, "sub_county": sub_county, "status": "ACTIVE" if active else "INACTIVE"}
    if registration_key:
        values["registration_number"] = registration_key
    for field, value in values.items():
        if value is not None and getattr(facility, field) != value:
            setattr(facility, field, value)
            changed = True
    return changed


def sync_kmhfr_facilities(db: Session, *, force: bool = False) -> int:
    global _last_kmhfr_sync_at, _kmhfr_sync_running
    now = datetime.now(timezone.utc)
    if not force and _last_kmhfr_sync_at and now - _last_kmhfr_sync_at < _KMHFR_SYNC_TTL:
        return 0
    base = os.getenv("KMHFR_API_BASE_URL", "https://api.kmhfr.health.go.ke/api/public").rstrip("/")
    token = os.getenv("KMHFR_API_TOKEN", "").strip()
    headers = {"Accept": "application/json", "User-Agent": "AfyaSync/1.0"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    url = f"{base}/facilities/"
    imported = 0
    pages = 0
    try:
        with httpx.Client(timeout=30.0, follow_redirects=True, headers=headers) as client:
            while url and pages < 1000:
                response = client.get(url, params={"page_size": 30} if pages == 0 else None)
                response.raise_for_status()
                payload = response.json()
                results = payload.get("results", payload if isinstance(payload, list) else [])
                if not isinstance(results, list):
                    raise ValueError("KMHFR_INVALID_RESULTS")
                for item in results:
                    if isinstance(item, dict) and _sync_kmhfr_page(item, db):
                        imported += 1
                db.commit()
                next_url = payload.get("next") if isinstance(payload, dict) else None
                url = next_url if isinstance(next_url, str) and next_url else ""
                pages += 1
                if pages % 25 == 0:
                    logger.info("KMHFR facility sync progress pages=%s imported_or_changed=%s", pages, imported)
    except Exception:
        db.rollback()
        logger.exception("KMHFR facility sync failed after pages=%s", pages)
        return 0
    _last_kmhfr_sync_at = now
    logger.info("KMHFR facility sync complete pages=%s imported_or_changed=%s", pages, imported)
    return imported


def start_kmhfr_sync_if_needed() -> None:
    global _kmhfr_sync_running
    with _kmhfr_sync_lock:
        if _kmhfr_sync_running:
            return
        now = datetime.now(timezone.utc)
        if _last_kmhfr_sync_at and now - _last_kmhfr_sync_at < _KMHFR_SYNC_TTL:
            return
        _kmhfr_sync_running = True
    def worker() -> None:
        global _kmhfr_sync_running
        try:
            with SessionLocal() as db:
                sync_kmhfr_facilities(db)
        finally:
            with _kmhfr_sync_lock:
                _kmhfr_sync_running = False
    threading.Thread(target=worker, name="kmhfr-facility-sync", daemon=True).start()


def get_facility(db: Session, facility_id: UUID) -> Facility | None:
    return db.get(Facility, facility_id)


def update_facility(db: Session, facility_id: UUID, data: dict, *, actor_user_id: UUID | None = None) -> Facility:
    facility = db.get(Facility, facility_id)
    if facility is None:
        raise ValueError("FACILITY_NOT_FOUND")
    changes = {k: v for k, v in data.items() if v is not None}
    if not changes:
        raise ValueError("NO_CHANGES")
    for field, value in changes.items():
        setattr(facility, field, value)
    db.flush()
    record_audit(db, action="UPDATE_FACILITY", resource_type="FACILITY", resource_id=str(facility.id), result="SUCCESS", user_id=actor_user_id, facility_id=facility_id, metadata={"changed_fields": sorted(changes.keys())}, commit=False)
    db.commit()
    db.refresh(facility)
    return facility


def update_facility_status(db: Session, facility_id: UUID, status: str, *, reason: str, actor_user_id: UUID | None = None) -> Facility:
    if status not in _ALLOWED_FACILITY_STATUSES:
        raise ValueError("INVALID_FACILITY_STATUS")
    normalized_reason = reason.strip()
    if len(normalized_reason) < 3:
        raise ValueError("FACILITY_STATUS_REASON_REQUIRED")
    facility = db.get(Facility, facility_id)
    if facility is None:
        raise ValueError("FACILITY_NOT_FOUND")
    if facility.status == status:
        raise ValueError("FACILITY_STATUS_UNCHANGED")
    if status not in _FACILITY_STATUS_TRANSITIONS.get(facility.status, set()):
        raise ValueError("INVALID_FACILITY_STATUS_TRANSITION")
    previous = facility.status
    facility.status = status
    db.flush()
    record_audit(db, action="UPDATE_FACILITY_STATUS", resource_type="FACILITY", resource_id=str(facility.id), result="SUCCESS", user_id=actor_user_id, facility_id=facility_id, metadata={"previous_status": previous, "new_status": status, "reason": normalized_reason}, commit=False)
    db.commit()
    db.refresh(facility)
    return facility


def create_department(db: Session, facility_id: UUID, data: dict, *, actor_user_id: UUID | None = None) -> Department:
    facility = db.get(Facility, facility_id)
    if facility is None:
        raise ValueError("FACILITY_NOT_FOUND")
    existing = db.scalar(select(Department).where(Department.facility_id == facility_id, Department.code == data["code"]))
    if existing is not None:
        raise ValueError("DEPARTMENT_CODE_EXISTS")
    department = Department(facility_id=facility_id, **data)
    db.add(department)
    db.flush()
    record_audit(db, action="CREATE_DEPARTMENT", resource_type="DEPARTMENT", resource_id=str(department.id), result="SUCCESS", user_id=actor_user_id, facility_id=facility_id, metadata={"name": department.name, "code": department.code}, commit=False)
    db.commit()
    db.refresh(department)
    return department


def list_departments(db: Session, facility_id: UUID) -> list[Department]:
    return list(db.scalars(select(Department).where(Department.facility_id == facility_id).order_by(Department.name)))


def update_department_status(db: Session, facility_id: UUID, department_id: UUID, status: str, *, actor_user_id: UUID | None = None) -> Department:
    if status not in _ALLOWED_DEPARTMENT_STATUSES:
        raise ValueError("INVALID_DEPARTMENT_STATUS")
    department = db.get(Department, department_id)
    if department is None or department.facility_id != facility_id:
        raise ValueError("DEPARTMENT_NOT_FOUND")
    if department.status == status:
        raise ValueError("DEPARTMENT_STATUS_UNCHANGED")
    previous = department.status
    department.status = status
    db.flush()
    record_audit(db, action="UPDATE_DEPARTMENT_STATUS", resource_type="DEPARTMENT", resource_id=str(department.id), result="SUCCESS", user_id=actor_user_id, facility_id=facility_id, metadata={"previous_status": previous, "new_status": status}, commit=False)
    db.commit()
    db.refresh(department)
    return department
