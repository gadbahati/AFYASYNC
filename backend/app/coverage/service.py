from datetime import date
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.coverage.models import Coverage, Payer, PayerPlan
from app.coverage.schemas import CoverageCreate


def create_coverage(db: Session, payload: CoverageCreate) -> Coverage:
    if payload.end_date and payload.start_date and payload.end_date < payload.start_date:
        raise ValueError("INVALID_COVERAGE_DATES")

    payer = db.get(Payer, payload.payer_id)
    if not payer or payer.status != "ACTIVE":
        raise ValueError("PAYER_NOT_FOUND")

    if payload.payer_plan_id:
        plan = db.get(PayerPlan, payload.payer_plan_id)
        if not plan or plan.payer_id != payload.payer_id or plan.status != "ACTIVE":
            raise ValueError("INVALID_PAYER_PLAN")

    coverage = Coverage(**payload.model_dump())
    db.add(coverage)
    db.commit()
    db.refresh(coverage)
    return coverage


def get_active_coverage(db: Session, person_id: UUID) -> list[Coverage]:
    today = date.today()
    statement = select(Coverage).where(
        Coverage.person_id == person_id,
        Coverage.status == "ACTIVE",
        (Coverage.start_date.is_(None) | (Coverage.start_date <= today)),
        (Coverage.end_date.is_(None) | (Coverage.end_date >= today)),
    ).order_by(Coverage.created_at.desc())
    return list(db.scalars(statement).all())
