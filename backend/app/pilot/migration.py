"""Migration readiness from legacy HMIS / paper / partial digital."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.encounters.models import Encounter
from app.facilities.models import Facility
from app.patients.models import Person

MIGRATION_DOMAINS = [
    {
        "id": "MIG-01",
        "title": "Facility master data complete",
        "detail": "Name, level, county, KMHFR/FID where available",
    },
    {
        "id": "MIG-02",
        "title": "Patient identity strategy agreed",
        "detail": "National ID hash + Afya ID; no duplicate persons without merge path",
    },
    {
        "id": "MIG-03",
        "title": "Service catalogue mapped to local tariffs",
        "detail": "Codes ready for SHA intervention mapping later",
    },
    {
        "id": "MIG-04",
        "title": "Historical data scope defined",
        "detail": "What moves (open episodes only vs 12-month history)",
    },
    {
        "id": "MIG-05",
        "title": "Staff RBAC roles assigned",
        "detail": "No shared passwords; least privilege",
    },
    {
        "id": "MIG-06",
        "title": "Backup and restore tested",
        "detail": "DB dump restore drill within RTO target",
    },
    {
        "id": "MIG-07",
        "title": "Dual-run period agreed",
        "detail": "Days of parallel paper/legacy vs AfyaSync",
    },
]


def migration_readiness(db: Session, *, facility_id=None) -> dict:
    """Automated counts + static migration domain list."""
    facility_count = db.scalar(select(func.count()).select_from(Facility)) or 0
    person_count = db.scalar(select(func.count()).select_from(Person)) or 0
    encounter_count = db.scalar(select(func.count()).select_from(Encounter)) or 0

    alembic_rev = None
    try:
        alembic_rev = db.execute(text("SELECT version_num FROM alembic_version")).scalar()
    except Exception:
        alembic_rev = None

    offline_ok = False
    try:
        offline_ok = bool(
            db.execute(
                text(
                    "SELECT 1 FROM information_schema.tables "
                    "WHERE table_schema='public' AND table_name='offline_outbox_events'"
                )
            ).scalar()
        )
    except Exception:
        offline_ok = False

    auto = {
        "facilities": int(facility_count),
        "persons": int(person_count),
        "encounters": int(encounter_count),
        "alembic_revision": alembic_rev,
        "offline_outbox_table_present": offline_ok,
        "facility_scope": str(facility_id) if facility_id else "all",
    }

    # Soft scoring: data present is good for pilot depth; empty is fine for greenfield
    score = 0
    score += 20 if facility_count >= 1 else 0
    score += 15 if alembic_rev else 0
    score += 15 if offline_ok else 0
    score += 10 if person_count >= 0 else 0  # always true — placeholder for structure
    score += 40  # domains documented (manual completion still required)

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "auto_metrics": auto,
        "domains": MIGRATION_DOMAINS,
        "readiness_score_hint": min(score, 100),
        "note": "Score is advisory. Pilot go-live requires signed dual-run plan.",
        "developer": "BAHATI GAD WANGWE",
    }
