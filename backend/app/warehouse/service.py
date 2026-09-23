"""De-identified national warehouse views + CSV export helpers."""

from __future__ import annotations

import csv
import io
from datetime import date, datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.ambulance.models import AmbulanceRequest
from app.claims.models import Claim
from app.encounters.models import Encounter
from app.facilities.models import Facility
from app.rbac.models import Staff
from app.surveillance.models import NotifiableEvent
from app.telemedicine.models import TeleConsultRequest


def _since(days: int) -> datetime:
    days = max(1, min(days, 365))
    return datetime.now(timezone.utc) - timedelta(days=days)


def national_fact_summary(db: Session, *, days: int = 30) -> dict:
    since = _since(days)
    since_date = date.today() - timedelta(days=days)

    facilities = db.scalar(
        select(func.count()).select_from(Facility).where(Facility.status == "ACTIVE")
    ) or 0
    staff = db.scalar(
        select(func.count()).select_from(Staff).where(Staff.status == "ACTIVE")
    ) or 0

    encounters = db.scalar(
        select(func.count()).select_from(Encounter).where(Encounter.created_at >= since)
    )
    if encounters is None:
        # some schemas use started_at
        try:
            encounters = db.scalar(
                select(func.count()).select_from(Encounter).where(
                    Encounter.started_at >= since
                )
            ) or 0
        except Exception:
            encounters = db.scalar(select(func.count()).select_from(Encounter)) or 0
    else:
        encounters = int(encounters)

    claims = db.scalar(
        select(func.count()).select_from(Claim).where(Claim.updated_at >= since)
    ) or 0

    notifiable = db.scalar(
        select(func.count()).select_from(NotifiableEvent).where(
            NotifiableEvent.notification_date >= since_date
        )
    ) or 0

    ambulance = db.scalar(
        select(func.count()).select_from(AmbulanceRequest).where(
            AmbulanceRequest.created_at >= since
        )
    )
    if ambulance is None:
        ambulance = db.scalar(select(func.count()).select_from(AmbulanceRequest)) or 0

    tele = db.scalar(
        select(func.count()).select_from(TeleConsultRequest).where(
            TeleConsultRequest.created_at >= since
        )
    )
    if tele is None:
        tele = db.scalar(select(func.count()).select_from(TeleConsultRequest)) or 0

    # Status breakdowns (no patient ids)
    claim_status = {
        str(s): int(c)
        for s, c in db.execute(
            select(Claim.status, func.count())
            .where(Claim.updated_at >= since)
            .group_by(Claim.status)
        ).all()
    }
    notif_by_condition = {
        str(code): int(c)
        for code, c in db.execute(
            select(NotifiableEvent.condition_code, func.count())
            .where(NotifiableEvent.notification_date >= since_date)
            .group_by(NotifiableEvent.condition_code)
        ).all()
    }

    return {
        "window_days": days,
        "since": since.isoformat(),
        "facts": {
            "active_facilities": int(facilities),
            "active_staff": int(staff),
            "encounters": int(encounters),
            "claims": int(claims),
            "notifiable_events": int(notifiable),
            "ambulance_requests": int(ambulance),
            "teleconsult_requests": int(tele),
        },
        "claim_status": claim_status,
        "notifiable_by_condition": notif_by_condition,
        "privacy": "Aggregates only — no patient identifiers",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "developer": "BAHATI GAD WANGWE",
    }


def county_fact_table(db: Session, *, days: int = 30) -> list[dict]:
    """Row-oriented county facts for export."""
    since = _since(days)

    rows = list(
        db.execute(
            select(
                Facility.county,
                func.count(func.distinct(Facility.id)),
            )
            .where(Facility.status == "ACTIVE")
            .group_by(Facility.county)
        ).all()
    )

    out = []
    for county, fac_count in rows:
        name = (county or "UNKNOWN").strip() or "UNKNOWN"
        enc = db.scalar(
            select(func.count())
            .select_from(Encounter)
            .join(Facility, Facility.id == Encounter.facility_id)
            .where(Facility.county == county, Facility.status == "ACTIVE")
        ) or 0
        claims = db.scalar(
            select(func.count())
            .select_from(Claim)
            .join(Encounter, Encounter.id == Claim.encounter_id)
            .join(Facility, Facility.id == Encounter.facility_id)
            .where(
                Facility.county == county,
                Facility.status == "ACTIVE",
                Claim.updated_at >= since,
            )
        ) or 0
        out.append(
            {
                "county": name,
                "active_facilities": int(fac_count),
                "encounters_all_time": int(enc),
                "claims_in_window": int(claims),
                "window_days": days,
            }
        )
    out.sort(key=lambda r: r["county"])
    return out


def export_csv(rows: list[dict], *, fieldnames: list[str] | None = None) -> str:
    if not rows:
        return ""
    fieldnames = fieldnames or list(rows[0].keys())
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()
    for row in rows:
        writer.writerow(row)
    return buf.getvalue()


def warehouse_catalog() -> dict:
    return {
        "views": [
            {
                "id": "national_fact_summary",
                "path": "/api/v1/warehouse/facts",
                "description": "National aggregate facts for a time window",
            },
            {
                "id": "county_fact_table",
                "path": "/api/v1/warehouse/county-facts",
                "description": "County-level facility/encounter/claim facts",
            },
            {
                "id": "county_facts_csv",
                "path": "/api/v1/warehouse/export/county-facts.csv",
                "description": "CSV export of county facts",
            },
        ],
        "privacy": "No patient-level rows in warehouse exports",
        "developer": "BAHATI GAD WANGWE",
    }
