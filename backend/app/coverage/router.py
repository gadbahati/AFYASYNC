from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user, get_facility_context, require_permission
from app.coverage.permissions import COVERAGE_BENEFIT_WRITE
from app.coverage.schemas import BenefitRuleCreate, BenefitRuleResponse, CoverageCreate, CoverageResponse
from app.coverage.service import create_benefit_rule, create_coverage, get_active_coverage
from app.database import get_db
from app.rbac.models import User

router = APIRouter(prefix="/api/v1/coverage", tags=["Coverage"])


@router.post("", response_model=CoverageResponse, status_code=status.HTTP_201_CREATED)
def add_coverage(
    payload: CoverageCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> CoverageResponse:
    try:
        coverage = create_coverage(db, payload, actor_user_id=user.id)
    except ValueError as exc:
        code = str(exc)
        messages = {
            "INVALID_COVERAGE_DATES": "Coverage end date cannot be before start date.",
            "PAYER_NOT_FOUND": "The selected payer is not available.",
            "INVALID_PAYER_PLAN": "The selected payer plan is invalid.",
        }
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={"code": code, "message": messages.get(code, code)}) from exc
    return coverage


@router.get("/person/{person_id}/active", response_model=list[CoverageResponse])
def active_coverage(
    person_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[CoverageResponse]:
    if user.person_id != person_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="COVERAGE_ACCESS_DENIED")
    return get_active_coverage(db, person_id)


@router.post("/benefit-rules", response_model=BenefitRuleResponse, status_code=status.HTTP_201_CREATED)
def add_benefit_rule(
    payload: BenefitRuleCreate,
    db: Session = Depends(get_db),
    facility_id: UUID = Depends(get_facility_context),
    user: User = Depends(require_permission(COVERAGE_BENEFIT_WRITE)),
) -> BenefitRuleResponse:
    _ = facility_id
    try:
        return create_benefit_rule(db, payload, actor_user_id=user.id)
    except ValueError as exc:
        code = str(exc)
        messages = {
            "INVALID_BENEFIT_DATES": "Benefit rule end date cannot be before its start date.",
            "PAYER_NOT_FOUND": "The selected payer is not available.",
            "INVALID_PAYER_PLAN": "The selected payer plan is invalid.",
        }
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={"code": code, "message": messages.get(code, code)}) from exc
