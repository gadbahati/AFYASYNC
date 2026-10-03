from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.dependencies import get_facility_context, require_permission
from app.benefit_engine.models import BenefitRuleVersion
from app.benefit_engine.schemas import (
    BenefitBatchQuoteRequest,
    BenefitQuoteRequest,
    BenefitQuoteResponse,
    BenefitRuleVersionCreate,
    BenefitRuleVersionOut,
)
from app.benefit_engine.service import quote, quote_lines
from app.coverage.permissions import COVERAGE_BENEFIT_WRITE, COVERAGE_READ
from app.database import get_db
from app.rbac.models import User

router = APIRouter(prefix="/api/v1/benefit-engine", tags=["Universal Benefits & Tariffs"])


@router.post("/rules", response_model=BenefitRuleVersionOut, status_code=201)
def create_rule(
    payload: BenefitRuleVersionCreate,
    db: Session = Depends(get_db),
    facility_id: UUID = Depends(get_facility_context),
    user: User = Depends(require_permission(COVERAGE_BENEFIT_WRITE)),
):
    _ = facility_id, user
    row = BenefitRuleVersion(**payload.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.get("/rules", response_model=list[BenefitRuleVersionOut])
def list_rules(
    payer_id: UUID | None = None,
    payer_plan_id: UUID | None = None,
    status: str | None = None,
    db: Session = Depends(get_db),
    facility_id: UUID = Depends(get_facility_context),
    user: User = Depends(require_permission(COVERAGE_READ)),
):
    _ = facility_id, user
    q = select(BenefitRuleVersion)
    if payer_id:
        q = q.where(BenefitRuleVersion.payer_id == payer_id)
    if payer_plan_id:
        q = q.where(BenefitRuleVersion.payer_plan_id == payer_plan_id)
    if status:
        q = q.where(BenefitRuleVersion.status == status)
    return list(
        db.scalars(
            q.order_by(BenefitRuleVersion.effective_from.desc(), BenefitRuleVersion.version.desc())
        ).all()
    )


@router.post("/quote", response_model=BenefitQuoteResponse)
def benefit_quote(
    payload: BenefitQuoteRequest,
    db: Session = Depends(get_db),
    facility_id: UUID = Depends(get_facility_context),
    user: User = Depends(require_permission(COVERAGE_READ)),
):
    _ = facility_id, user
    return quote(db, payload)


@router.post("/quote-batch")
def benefit_quote_batch(
    payload: BenefitBatchQuoteRequest,
    db: Session = Depends(get_db),
    facility_id: UUID = Depends(get_facility_context),
    user: User = Depends(require_permission(COVERAGE_READ)),
):
    """Phase 103 — multi-line quote for claims/invoice adjudication input."""
    _ = facility_id, user
    return quote_lines(
        db,
        payer_id=payload.payer_id,
        payer_plan_id=payload.payer_plan_id,
        package_id=payload.benefit_package_id,
        as_of=payload.as_of,
        lines=[line.model_dump() for line in payload.lines],
    )
