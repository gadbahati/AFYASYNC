from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.auth.dependencies import require_national_permission
from app.coverage.payer_admin_schemas import (
    PayerAdminResponse, PayerCreate, PayerPlanAdminResponse, PayerPlanCreate,
    PayerPlanStatusUpdate, PayerPlanUpdate, PayerStatusUpdate, PayerUpdate,
)
from app.coverage.payer_admin_service import (
    create_network_payer, create_network_payer_plan, list_network_payer_plans,
    list_network_payers, update_network_payer, update_network_payer_plan,
    update_network_payer_plan_status, update_network_payer_status,
)
from app.database import get_db
from app.rbac.models import User

router = APIRouter(prefix="/api/v1/payer-network", tags=["National Payer Network"])


def _error(code: str) -> HTTPException:
    return HTTPException(status_code={
        "PAYER_NOT_FOUND": 404, "PAYER_PLAN_NOT_FOUND": 404,
        "PAYER_CODE_EXISTS": 409, "PAYER_PLAN_CODE_EXISTS": 409,
        "PAYER_STATUS_UNCHANGED": 409, "PAYER_PLAN_STATUS_UNCHANGED": 409,
        "INVALID_PAYER_STATUS_TRANSITION": 409, "PAYER_NOT_ACTIVE": 409,
        "NO_CHANGES": 400, "INVALID_PAYER_PLAN_STATUS": 400,
    }.get(code, 400), detail=code)


@router.get("/payers", response_model=list[PayerAdminResponse])
def get_payers(
    status_filter: str | None = Query(default=None, alias="status"),
    db: Session = Depends(get_db),
    _: User = Depends(require_national_permission("payer.network.read")),
) -> list[PayerAdminResponse]:
    return list_network_payers(db, status_filter)


@router.post("/payers", response_model=PayerAdminResponse, status_code=status.HTTP_201_CREATED)
def create_payer(
    payload: PayerCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_national_permission("payer.network.manage")),
) -> PayerAdminResponse:
    try:
        return create_network_payer(db, payload, actor_user_id=user.id)
    except ValueError as exc:
        raise _error(str(exc)) from exc


@router.patch("/payers/{payer_id}", response_model=PayerAdminResponse)
def update_payer(
    payer_id: UUID,
    payload: PayerUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_national_permission("payer.network.manage")),
) -> PayerAdminResponse:
    try:
        return update_network_payer(db, payer_id, payload, actor_user_id=user.id)
    except ValueError as exc:
        raise _error(str(exc)) from exc


@router.patch("/payers/{payer_id}/status", response_model=PayerAdminResponse)
def change_payer_status(
    payer_id: UUID,
    payload: PayerStatusUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_national_permission("payer.network.manage")),
) -> PayerAdminResponse:
    try:
        return update_network_payer_status(db, payer_id, payload.status, payload.reason, actor_user_id=user.id)
    except ValueError as exc:
        raise _error(str(exc)) from exc


@router.get("/payers/{payer_id}/plans", response_model=list[PayerPlanAdminResponse])
def get_payer_plans(
    payer_id: UUID,
    status_filter: str | None = Query(default=None, alias="status"),
    db: Session = Depends(get_db),
    _: User = Depends(require_national_permission("payer.network.read")),
) -> list[PayerPlanAdminResponse]:
    try:
        return list_network_payer_plans(db, payer_id, status_filter)
    except ValueError as exc:
        raise _error(str(exc)) from exc


@router.post("/payers/{payer_id}/plans", response_model=PayerPlanAdminResponse, status_code=status.HTTP_201_CREATED)
def create_payer_plan(
    payer_id: UUID,
    payload: PayerPlanCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_national_permission("payer.network.manage")),
) -> PayerPlanAdminResponse:
    try:
        return create_network_payer_plan(db, payer_id, payload, actor_user_id=user.id)
    except ValueError as exc:
        raise _error(str(exc)) from exc


@router.patch("/plans/{plan_id}", response_model=PayerPlanAdminResponse)
def update_payer_plan(
    plan_id: UUID,
    payload: PayerPlanUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_national_permission("payer.network.manage")),
) -> PayerPlanAdminResponse:
    try:
        return update_network_payer_plan(db, plan_id, payload, actor_user_id=user.id)
    except ValueError as exc:
        raise _error(str(exc)) from exc


@router.patch("/plans/{plan_id}/status", response_model=PayerPlanAdminResponse)
def change_payer_plan_status(
    plan_id: UUID,
    payload: PayerPlanStatusUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_national_permission("payer.network.manage")),
) -> PayerPlanAdminResponse:
    try:
        return update_network_payer_plan_status(db, plan_id, payload.status, actor_user_id=user.id)
    except ValueError as exc:
        raise _error(str(exc)) from exc
