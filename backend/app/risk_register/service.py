"""Seed catalogue + residual risk CRUD workflow."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit.service import record_audit
from app.risk_register.models import ResidualRisk

LEVELS = {"LOW", "MEDIUM", "HIGH", "CRITICAL"}
STATUSES = {"OPEN", "MITIGATED", "ACCEPTED", "CLOSED"}
CATEGORIES = {"SECURITY", "PRIVACY", "OPS", "COMPLIANCE", "INTEGRATION"}
TREATMENTS = {"MITIGATE", "ACCEPT", "TRANSFER", "AVOID"}

DEFAULT_RISKS = [
    {
        "code": "RR-SHA-LIVE",
        "title": "Live SHA credentials not yet operator-owned",
        "category": "INTEGRATION",
        "inherent_level": "HIGH",
        "residual_level": "MEDIUM",
        "description": "Production claims path depends on live SHA/DHA credentials supplied by operator",
        "controls": "Mock/live client switch; sandbox contracts; no secrets in repo",
        "treatment": "MITIGATE",
        "owner": "National ops / facility IT",
    },
    {
        "code": "RR-PENTEST",
        "title": "External penetration test pending",
        "category": "SECURITY",
        "inherent_level": "HIGH",
        "residual_level": "MEDIUM",
        "description": "Independent offensive security assessment not yet filed",
        "controls": "Security headers; JWT auth; rate limits; audit trail; privacy-safe logs",
        "treatment": "MITIGATE",
        "owner": "Security officer",
    },
    {
        "code": "RR-DHA-CERT",
        "title": "DHA certification filing pending",
        "category": "COMPLIANCE",
        "inherent_level": "HIGH",
        "residual_level": "MEDIUM",
        "description": "Formal DHA portal certification evidence not yet submitted",
        "controls": "Submission kit API; certification evidence pack; interoperability modules",
        "treatment": "MITIGATE",
        "owner": "Compliance lead",
    },
    {
        "code": "RR-BACKUP-RESTORE",
        "title": "Full restore drill evidence incomplete",
        "category": "OPS",
        "inherent_level": "HIGH",
        "residual_level": "MEDIUM",
        "description": "Backup verification records exist; full RTO/RPO drill may still be outstanding",
        "controls": "DR checklist; backup verification API; /ready after restore",
        "treatment": "MITIGATE",
        "owner": "Platform ops",
    },
    {
        "code": "RR-PII-ERASURE",
        "title": "Erasure vs legal retention tension",
        "category": "PRIVACY",
        "inherent_level": "MEDIUM",
        "residual_level": "LOW",
        "description": "Right-to-erasure balanced against claims/audit retention duties",
        "controls": "Pseudonymisation on fulfil; retention catalogue; audit of decisions",
        "treatment": "ACCEPT",
        "owner": "Data protection officer",
    },
    {
        "code": "RR-LOAD-SCALE",
        "title": "National load proof external",
        "category": "OPS",
        "inherent_level": "MEDIUM",
        "residual_level": "LOW",
        "description": "Process metrics evaluated; 1000-user national load requires external lab",
        "controls": "Performance acceptance API; observability SLOs; recommended k6/Locust",
        "treatment": "MITIGATE",
        "owner": "Platform ops",
    },
]


class RiskError(ValueError):
    pass


def seed_defaults(db: Session) -> dict:
    created = 0
    for item in DEFAULT_RISKS:
        exists = db.scalar(select(ResidualRisk).where(ResidualRisk.code == item["code"]))
        if exists is not None:
            continue
        db.add(
            ResidualRisk(
                code=item["code"],
                title=item["title"],
                category=item["category"],
                inherent_level=item["inherent_level"],
                residual_level=item["residual_level"],
                description=item["description"],
                controls=item["controls"],
                treatment=item["treatment"],
                owner=item["owner"],
                status="OPEN",
            )
        )
        created += 1
    if created:
        db.flush()
    return {"seeded": created, "catalogue_size": len(DEFAULT_RISKS)}


def _ser(r: ResidualRisk) -> dict:
    return {
        "id": str(r.id),
        "code": r.code,
        "title": r.title,
        "category": r.category,
        "inherent_level": r.inherent_level,
        "residual_level": r.residual_level,
        "status": r.status,
        "description": r.description,
        "controls": r.controls,
        "owner": r.owner,
        "treatment": r.treatment,
        "updated_at": r.updated_at.isoformat() if r.updated_at else None,
    }


def list_risks(
    db: Session, *, status: str | None = None, category: str | None = None, limit: int = 100
) -> list[dict]:
    limit = max(1, min(limit, 200))
    q = select(ResidualRisk)
    if status:
        q = q.where(ResidualRisk.status == status.strip().upper())
    if category:
        q = q.where(ResidualRisk.category == category.strip().upper())
    rows = db.scalars(q.order_by(ResidualRisk.code.asc()).limit(limit)).all()
    return [_ser(r) for r in rows]


def update_risk(
    db: Session,
    *,
    risk_id: UUID,
    status: str | None = None,
    residual_level: str | None = None,
    treatment: str | None = None,
    controls: str | None = None,
    owner: str | None = None,
    actor_user_id: UUID | None = None,
) -> ResidualRisk:
    row = db.get(ResidualRisk, risk_id)
    if row is None:
        raise RiskError("RISK_NOT_FOUND")

    if status is not None:
        st = status.strip().upper()
        if st not in STATUSES:
            raise RiskError("INVALID_STATUS")
        row.status = st
    if residual_level is not None:
        rl = residual_level.strip().upper()
        if rl not in LEVELS:
            raise RiskError("INVALID_RESIDUAL_LEVEL")
        row.residual_level = rl
    if treatment is not None:
        tr = treatment.strip().upper()
        if tr not in TREATMENTS:
            raise RiskError("INVALID_TREATMENT")
        row.treatment = tr
    if controls is not None:
        row.controls = controls.strip()[:4000] or None
    if owner is not None:
        row.owner = owner.strip()[:120] or None

    row.reviewed_by_user_id = actor_user_id
    db.flush()
    record_audit(
        db,
        action="RESIDUAL_RISK_UPDATE",
        resource_type="RESIDUAL_RISK",
        resource_id=str(row.id),
        result=row.status,
        user_id=actor_user_id,
        metadata={"code": row.code, "residual_level": row.residual_level},
        commit=False,
    )
    return row


def posture(db: Session) -> dict:
    seed_defaults(db)
    rows = list_risks(db, limit=200)
    open_count = sum(1 for r in rows if r["status"] == "OPEN")
    accepted = sum(1 for r in rows if r["status"] == "ACCEPTED")
    critical_open = sum(
        1 for r in rows if r["status"] == "OPEN" and r["residual_level"] in {"HIGH", "CRITICAL"}
    )

    if critical_open > 0:
        band = "RED"
    elif open_count > 3:
        band = "AMBER"
    else:
        band = "GREEN"

    return {
        "band": band,
        "total": len(rows),
        "open": open_count,
        "accepted": accepted,
        "critical_or_high_open": critical_open,
        "risks": rows,
        "note": "Residual risk is managed, not eliminated — acceptances require accountable owner",
        "developer": "BAHATI GAD WANGWE",
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
