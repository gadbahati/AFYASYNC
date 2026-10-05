"""Terminology lookup and mapping service."""
from uuid import UUID
from sqlalchemy import select, or_
from sqlalchemy.orm import Session
from app.hie.terminology_models import TerminologyConcept, TerminologyMapping

KENYA_CORE_BASE = "https://fhir.dha.go.ke/terminology/"

def search_concepts(db: Session, system: str | None = None, code: str | None = None, text: str | None = None, limit: int = 50):
    q = select(TerminologyConcept).where(TerminologyConcept.status == "ACTIVE")
    if system: q = q.where(TerminologyConcept.system == system)
    if code: q = q.where(TerminologyConcept.code == code)
    if text:
        term = f"%{text.strip()}%"
        q = q.where(or_(TerminologyConcept.code.ilike(term), TerminologyConcept.display.ilike(term)))
    return list(db.scalars(q.order_by(TerminologyConcept.display).limit(limit)))

def validate_code(db: Session, system: str, code: str, version: str | None = None):
    q = select(TerminologyConcept).where(TerminologyConcept.system == system, TerminologyConcept.code == code, TerminologyConcept.status == "ACTIVE")
    if version is not None: q = q.where(TerminologyConcept.version == version)
    return db.scalar(q)

def map_code(db: Session, source_system: str, source_code: str, target_system: str):
    return list(db.scalars(select(TerminologyMapping).where(
        TerminologyMapping.source_system == source_system,
        TerminologyMapping.source_code == source_code,
        TerminologyMapping.target_system == target_system,
        TerminologyMapping.status == "ACTIVE",
    )))

def upsert_concept(db: Session, *, data: dict, actor_user_id: UUID | None):
    existing = db.scalar(select(TerminologyConcept).where(
        TerminologyConcept.system == data["system"],
        TerminologyConcept.version == data.get("version"),
        TerminologyConcept.code == data["code"],
    ))
    if existing:
        for key in ("display","definition","status","properties","source"):
            if key in data: setattr(existing,key,data[key])
        return existing
    row=TerminologyConcept(**data,created_by=actor_user_id)
    db.add(row); db.flush(); return row

def upsert_mapping(db: Session, *, data: dict, actor_user_id: UUID | None):
    existing=db.scalar(select(TerminologyMapping).where(
        TerminologyMapping.source_system==data["source_system"],
        TerminologyMapping.source_code==data["source_code"],
        TerminologyMapping.target_system==data["target_system"],
        TerminologyMapping.target_code==data["target_code"],
    ))
    if existing:
        for key in ("equivalence","source_display","target_display","status","provenance"):
            if key in data: setattr(existing,key,data[key])
        return existing
    row=TerminologyMapping(**data,created_by=actor_user_id)
    db.add(row); db.flush(); return row


def canonical_coding(db: Session, *, source_system: str, source_code: str | None, display: str | None = None) -> dict | None:
    """Return a verified target coding only when an explicit registry mapping exists."""
    if not source_code:
        return None
    rows = list(db.scalars(select(TerminologyMapping).where(
        TerminologyMapping.source_system == source_system,
        TerminologyMapping.source_code == source_code,
        TerminologyMapping.status == "ACTIVE",
    ).limit(10)))
    # Never choose an arbitrary mapping when local data is ambiguous.
    if len(rows) != 1:
        return None
    row = rows[0]
    target = db.scalar(select(TerminologyConcept).where(
        TerminologyConcept.system == row.target_system,
        TerminologyConcept.code == row.target_code,
        TerminologyConcept.status == "ACTIVE",
    ))
    # A mapping is usable only when its target is present in the active
    # terminology registry. This prevents stale or fabricated national codes.
    if target is None:
        return None
    return {
        "system": row.target_system,
        "code": row.target_code,
        "display": row.target_display or target.display or display,
    }
