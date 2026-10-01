from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.auth.dependencies import get_facility_context, require_permission
from app.database import get_db
from app.rbac.models import User
from app.financial_intelligence.service import financial_overview, forecast, payer_performance

router = APIRouter(prefix="/api/v1/financial-intelligence", tags=["Financial Intelligence"])


@router.get("/overview")
def overview(
    days: int = Query(default=90, ge=7, le=365),
    db: Session = Depends(get_db),
    facility_id: UUID = Depends(get_facility_context),
    user: User = Depends(require_permission("claims.reconcile")),
):
    _ = user
    return financial_overview(db, facility_id, days)


@router.get("/forecast")
def financial_forecast(
    days: int = Query(default=90, ge=7, le=365),
    db: Session = Depends(get_db),
    facility_id: UUID = Depends(get_facility_context),
    user: User = Depends(require_permission("claims.reconcile")),
):
    _ = user
    return forecast(db, facility_id, days)


@router.get("/payers")
def financial_payers(
    days: int = Query(default=90, ge=7, le=365),
    db: Session = Depends(get_db),
    facility_id: UUID = Depends(get_facility_context),
    user: User = Depends(require_permission("claims.reconcile")),
):
    _ = user
    return payer_performance(db, facility_id, days)
