"""Public-health style aggregates — no patient identifiers in output."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.clinical.models import Diagnosis
from app.encounters.models import Encounter
from app.patients.models import Person


def public_health_summary(
    db: Session,
    *,
    facility_id: UUID | None = None,
    days: int = 30,
) -> dict:
    """Aggregate encounter and diagnosis counts for surveillance-style views."""
    days = max(1, min(days, 365))
    since = datetime.now(timezone.utc) - timedelta(days=days)

    enc_q = select(Encounter.status, func.count()).where(Encounter.created_at >= since)
    if facility_id is not None:
        enc_q = enc_q.where(Encounter.facility_id == facility_id)
    enc_q = enc_q.group_by(Encounter.status)
    by_status = {str(s): int(c) for s, c in db.execute(enc_q).all()}

    mode_q = select(Encounter.coverage_mode, func.count()).where(Encounter.created_at >= since)
    if facility_id is not None:
        mode_q = mode_q.where(Encounter.facility_id == facility_id)
    mode_q = mode_q.group_by(Encounter.coverage_mode)
    by_coverage = {str(m or "UNKNOWN"): int(c) for m, c in db.execute(mode_q).all()}

    # Top diagnosis codes — codes only, no names of patients
    dx_q = (
        select(Diagnosis.diagnosis_code, func.count())
        .select_from(Diagnosis)
        .join(Encounter, Encounter.id == Diagnosis.encounter_id)
        .where(Encounter.created_at >= since, Diagnosis.diagnosis_code.isnot(None))
    )
    if facility_id is not None:
        dx_q = dx_q.where(Encounter.facility_id == facility_id)
    dx_q = dx_q.group_by(Diagnosis.diagnosis_code).order_by(func.count().desc()).limit(25)
    top_codes = [
        {"code": str(code), "count": int(count)}
        for code, count in db.execute(dx_q).all()
        if code
    ]

    # Age band distribution from persons linked to recent encounters (aggregate only)
    age_bands = {"0-4": 0, "5-14": 0, "15-24": 0, "25-49": 0, "50-64": 0, "65+": 0, "unknown": 0}
    today = date.today()
    person_q = (
        select(Person.date_of_birth)
        .select_from(Encounter)
        .join(Person, Person.id == Encounter.patient_id)
        .where(Encounter.created_at >= since)
    )
    if facility_id is not None:
        person_q = person_q.where(Encounter.facility_id == facility_id)
    for dob in db.scalars(person_q.limit(5000)).all():
        if not dob:
            age_bands["unknown"] += 1
            continue
        age = (today - dob).days // 365
        if age < 5:
            age_bands["0-4"] += 1
        elif age < 15:
            age_bands["5-14"] += 1
        elif age < 25:
            age_bands["15-24"] += 1
        elif age < 50:
            age_bands["25-49"] += 1
        elif age < 65:
            age_bands["50-64"] += 1
        else:
            age_bands["65+"] += 1

    return {
        "scope": "facility" if facility_id else "national_sample",
        "facility_id": str(facility_id) if facility_id else None,
        "window_days": days,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "encounters_by_status": by_status,
        "encounters_by_coverage_mode": by_coverage,
        "top_diagnosis_codes": top_codes,
        "age_bands": age_bands,
        "privacy": "Aggregates only — no patient identifiers in this payload",
        "developer": "BAHATI GAD WANGWE",
    }
