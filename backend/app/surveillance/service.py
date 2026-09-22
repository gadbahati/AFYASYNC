"""Notifiable event capture and de-identified surveillance aggregates."""

from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.audit.service import record_audit
from app.facilities.models import Facility
from app.patients.models import Person
from app.rbac.models import Staff
from app.surveillance.models import NotifiableEvent

KNOWN_CONDITIONS = {
    "MALARIA": "Malaria",
    "CHOLERA": "Cholera",
    "MEASLES": "Measles",
    "TB": "Tuberculosis",
    "COVID19": "COVID-19",
    "AFP": "Acute flaccid paralysis",
    "YELLOW_FEVER": "Yellow fever",
    "MENINGITIS": "Meningitis",
    "OTHER": "Other notifiable",
}
CLASSIFICATIONS = {"SUSPECTED", "PROBABLE", "CONFIRMED", "DISCARDED"}
STATUSES = {"OPEN", "SUBMITTED", "ACKNOWLEDGED", "CLOSED"}


class SurveillanceError(ValueError):
    pass


def _ser(e: NotifiableEvent) -> dict:
    return {
        "id": str(e.id),
        "facility_id": str(e.facility_id),
        "person_id": str(e.person_id) if e.person_id else None,
        "condition_code": e.condition_code,
        "condition_name": e.condition_name,
        "onset_date": e.onset_date.isoformat() if e.onset_date else None,
        "notification_date": e.notification_date.isoformat() if e.notification_date else None,
        "classification": e.classification,
        "status": e.status,
        "notes": e.notes,
        "created_at": e.created_at.isoformat() if e.created_at else None,
    }


def report_event(
    db: Session,
    *,
    facility_id: UUID,
    condition_code: str,
    classification: str = "SUSPECTED",
    person_id: UUID | None = None,
    onset_date: date | None = None,
    notification_date: date | None = None,
    notes: str | None = None,
    staff_id: UUID | None = None,
    actor_user_id: UUID | None = None,
) -> NotifiableEvent:
    fac = db.get(Facility, facility_id)
    if fac is None or fac.status != "ACTIVE":
        raise SurveillanceError("FACILITY_NOT_AVAILABLE")

    code = condition_code.strip().upper().replace(" ", "_")
    if not code:
        raise SurveillanceError("CONDITION_REQUIRED")
    name = KNOWN_CONDITIONS.get(code, code.replace("_", " ").title()[:120])

    cls = (classification or "SUSPECTED").strip().upper()
    if cls not in CLASSIFICATIONS:
        raise SurveillanceError("INVALID_CLASSIFICATION")

    if person_id is not None and db.get(Person, person_id) is None:
        raise SurveillanceError("PERSON_NOT_FOUND")

    if staff_id is not None:
        staff = db.get(Staff, staff_id)
        if staff is None or staff.facility_id != facility_id:
            raise SurveillanceError("STAFF_NOT_FOUND")

    event = NotifiableEvent(
        facility_id=facility_id,
        person_id=person_id,
        condition_code=code[:40],
        condition_name=name,
        onset_date=onset_date,
        notification_date=notification_date or date.today(),
        classification=cls,
        status="OPEN",
        notes=(notes or "").strip()[:2000] or None,
        reported_by_staff_id=staff_id,
    )
    db.add(event)
    db.flush()
    record_audit(
        db,
        action="NOTIFIABLE_EVENT_REPORT",
        resource_type="NOTIFIABLE_EVENT",
        resource_id=str(event.id),
        result="OPEN",
        user_id=actor_user_id,
        facility_id=facility_id,
        patient_id=person_id,
        metadata={"condition": code, "classification": cls},
        commit=False,
    )
    return event


def update_status(
    db: Session,
    *,
    facility_id: UUID,
    event_id: UUID,
    status: str,
    classification: str | None = None,
    notes: str | None = None,
    actor_user_id: UUID | None = None,
) -> NotifiableEvent:
    event = db.get(NotifiableEvent, event_id)
    if event is None or event.facility_id != facility_id:
        raise SurveillanceError("EVENT_NOT_FOUND")

    st = status.strip().upper()
    if st not in STATUSES:
        raise SurveillanceError("INVALID_STATUS")
    event.status = st
    if classification:
        cls = classification.strip().upper()
        if cls not in CLASSIFICATIONS:
            raise SurveillanceError("INVALID_CLASSIFICATION")
        event.classification = cls
    if notes is not None:
        event.notes = notes.strip()[:2000] or None
    db.flush()
    record_audit(
        db,
        action="NOTIFIABLE_EVENT_UPDATE",
        resource_type="NOTIFIABLE_EVENT",
        resource_id=str(event.id),
        result=st,
        user_id=actor_user_id,
        facility_id=facility_id,
        commit=False,
    )
    return event


def list_facility(
    db: Session,
    *,
    facility_id: UUID,
    status: str | None = None,
    condition_code: str | None = None,
    limit: int = 50,
) -> list[dict]:
    limit = max(1, min(limit, 200))
    q = select(NotifiableEvent).where(NotifiableEvent.facility_id == facility_id)
    if status:
        q = q.where(NotifiableEvent.status == status.strip().upper())
    if condition_code:
        q = q.where(NotifiableEvent.condition_code == condition_code.strip().upper())
    rows = db.scalars(q.order_by(NotifiableEvent.notification_date.desc()).limit(limit)).all()
    return [_ser(e) for e in rows]


def aggregate(
    db: Session,
    *,
    days: int = 30,
    county: str | None = None,
    facility_id: UUID | None = None,
) -> dict:
    """De-identified counts only — no person identifiers."""
    days = max(1, min(days, 365))
    since = date.today() - timedelta(days=days)

    q = (
        select(
            NotifiableEvent.condition_code,
            NotifiableEvent.classification,
            func.count(),
        )
        .join(Facility, Facility.id == NotifiableEvent.facility_id)
        .where(NotifiableEvent.notification_date >= since)
        .group_by(NotifiableEvent.condition_code, NotifiableEvent.classification)
    )
    if facility_id:
        q = q.where(NotifiableEvent.facility_id == facility_id)
    if county:
        q = q.where(Facility.county == county.strip())

    by_condition: dict[str, dict] = defaultdict(lambda: {"total": 0, "by_class": {}})
    for code, cls, cnt in db.execute(q).all():
        by_condition[str(code)]["total"] += int(cnt)
        by_condition[str(code)]["by_class"][str(cls)] = int(cnt)

    open_count = db.scalar(
        select(func.count()).select_from(NotifiableEvent).where(
            NotifiableEvent.status.in_(["OPEN", "SUBMITTED"]),
            NotifiableEvent.notification_date >= since,
        )
    ) or 0

    return {
        "window_days": days,
        "since": since.isoformat(),
        "county": county,
        "facility_id": str(facility_id) if facility_id else None,
        "open_or_submitted": int(open_count),
        "by_condition": dict(by_condition),
        "privacy": "Aggregates only — no patient identifiers",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "developer": "BAHATI GAD WANGWE",
    }
