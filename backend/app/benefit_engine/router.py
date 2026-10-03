from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, ValidationError
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


class BenefitRuleBulkImport(BaseModel):
    rules: list[BenefitRuleVersionCreate] = Field(min_length=1, max_length=500)
    stop_on_error: bool = False


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


@router.post("/rules/import")
def import_rules(
    payload: BenefitRuleBulkImport,
    db: Session = Depends(get_db),
    facility_id: UUID = Depends(get_facility_context),
    user: User = Depends(require_permission(COVERAGE_BENEFIT_WRITE)),
):
    """Bulk-create benefit rule versions (tariff pack). Phase 114."""
    _ = facility_id, user
    created: list[dict] = []
    errors: list[dict] = []
    for idx, rule in enumerate(payload.rules):
        try:
            row = BenefitRuleVersion(**rule.model_dump())
            db.add(row)
            db.flush()
            created.append(
                {
                    "index": idx,
                    "id": str(row.id),
                    "name": row.name,
                    "service_code": row.service_code,
                    "status": row.status,
                }
            )
        except Exception as exc:
            errors.append({"index": idx, "error": str(exc), "name": getattr(rule, "name", None)})
            if payload.stop_on_error:
                db.rollback()
                raise HTTPException(
                    status_code=400,
                    detail={"code": "BULK_IMPORT_FAILED", "index": idx, "error": str(exc)},
                ) from exc
    if created:
        db.commit()
    else:
        db.rollback()
    return {
        "created_count": len(created),
        "error_count": len(errors),
        "created": created,
        "errors": errors,
        "developer": "BAHATI GAD WANGWE",
    }


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
    _ = facility_id, user
    return quote_lines(
        db,
        payer_id=payload.payer_id,
        payer_plan_id=payload.payer_plan_id,
        package_id=payload.benefit_package_id,
        as_of=payload.as_of,
        lines=[ln.model_dump() for ln in payload.lines],
    )
