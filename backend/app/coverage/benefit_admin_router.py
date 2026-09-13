from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.auth.dependencies import require_national_permission
from app.coverage.benefit_admin_schemas import (
    BenefitRuleAdminCreate,
    BenefitRuleAdminResponse,
    BenefitRuleAdminUpdate,
    BenefitRuleStatusUpdate,
)
from app.coverage.benefit_admin_service import (
    create_network_benefit_rule,
    list_network_benefit_rules,
    update_network_benefit_rule,
    update_network_benefit_rule_status,
)
from app.database import get_db
from app.rbac.models import User


BENEFIT_NETWORK_READ = "benefit.network.read"
BENEFIT_NETWORK_MANAGE = "benefit.network.manage"

router = APIRouter(prefix="/api/v1/benefit-network", tags=["National Benefit Configuration"])


@router.get("/rules", response_model=list[BenefitRuleAdminResponse])
def list_rules(
    payer_id: UUID | None = Query(default=None),
    payer_plan_id: UUID | None = Query(default=None),
    rule_status: str | None = Query(default=None),
    db: Session = Depends(get_db),
    _: User = Depends(require_national_permission(BENEFIT_NETWORK_READ)),
) -> list[BenefitRuleAdminResponse]:
    return list_network_benefit_rules(db, payer_id, payer_plan_id, rule_status)


@router.post("/rules", response_model=BenefitRuleAdminResponse, status_code=status.HTTP_201_CREATED)
def create_rule(
    payload: BenefitRuleAdminCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_national_permission(BENEFIT_NETWORK_MANAGE)),
) -> BenefitRuleAdminResponse:
    try:
        return create_network_benefit_rule(db, payload, actor_user_id=user.id)
    except ValueError as exc:
        code = str(exc)
        messages = {
            "PAYER_NOT_FOUND": "The selected payer does not exist.",
            "PAYER_NOT_ACTIVE": "The payer must be active before benefit rules can be configured.",
            "INVALID_PAYER_PLAN": "The selected plan does not belong to the payer.",
            "PAYER_PLAN_NOT_ACTIVE": "The selected payer plan must be active.",
            "BENEFIT_SCOPE_REQUIRED": "Provide a service code or service type.",
            "INVALID_BENEFIT_DATES": "Benefit rule end date cannot be before its start date.",
        }
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={"code": code, "message": messages.get(code, code)}) from exc


@router.patch("/rules/{rule_id}", response_model=BenefitRuleAdminResponse)
def update_rule(
    rule_id: UUID,
    payload: BenefitRuleAdminUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_national_permission(BENEFIT_NETWORK_MANAGE)),
) -> BenefitRuleAdminResponse:
    try:
        return update_network_benefit_rule(db, rule_id, payload, actor_user_id=user.id)
    except ValueError as exc:
        code = str(exc)
        messages = {
            "BENEFIT_RULE_NOT_FOUND": "Benefit rule not found.",
            "NO_CHANGES": "No changes were supplied.",
            "BENEFIT_SCOPE_REQUIRED": "A benefit rule must retain a service code or service type.",
            "INVALID_BENEFIT_DATES": "Benefit rule end date cannot be before its start date.",
        }
        raise HTTPException(status_code=404 if code == "BENEFIT_RULE_NOT_FOUND" else 400, detail={"code": code, "message": messages.get(code, code)}) from exc


@router.patch("/rules/{rule_id}/status", response_model=BenefitRuleAdminResponse)
def update_rule_status(
    rule_id: UUID,
    payload: BenefitRuleStatusUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_national_permission(BENEFIT_NETWORK_MANAGE)),
) -> BenefitRuleAdminResponse:
    try:
        return update_network_benefit_rule_status(db, rule_id, payload.status, payload.reason, actor_user_id=user.id)
    except ValueError as exc:
        code = str(exc)
        messages = {
            "BENEFIT_RULE_NOT_FOUND": "Benefit rule not found.",
            "INVALID_BENEFIT_RULE_STATUS": "Benefit rule status must be ACTIVE or INACTIVE.",
            "BENEFIT_RULE_STATUS_UNCHANGED": "The benefit rule is already in that status.",
        }
        raise HTTPException(status_code=404 if code == "BENEFIT_RULE_NOT_FOUND" else 409 if code == "BENEFIT_RULE_STATUS_UNCHANGED" else 400, detail={"code": code, "message": messages.get(code, code)}) from exc
