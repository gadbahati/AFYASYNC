from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.auth.dependencies import get_facility_context, require_permission
from app.database import get_db
from app.rbac.models import User
from app.revenue_anomaly.schemas import AnomalyCaseOut, AnomalyCaseUpdate
from app.revenue_anomaly.service import RevenueAnomalyError, case_events, list_cases, overview, scan_facility, update_case

router = APIRouter(prefix="/api/v1/revenue-anomalies", tags=["Revenue Anomalies"])


@router.get("/overview")
def anomaly_overview(
    db: Session = Depends(get_db),
    facility_id: UUID = Depends(get_facility_context),
    user: User = Depends(require_permission("claims.reconcile")),
):
    _ = user
    return overview(db, facility_id)


@router.post("/scan")
def anomaly_scan(
    days: int = Query(default=30, ge=7, le=90),
    db: Session = Depends(get_db),
    facility_id: UUID = Depends(get_facility_context),
    user: User = Depends(require_permission("claims.reconcile")),
):
    return scan_facility(db, facility_id=facility_id, days=days, actor_id=user.id)


@router.get("/cases", response_model=list[AnomalyCaseOut])
def anomaly_cases(
    status: str | None = Query(default=None),
    db: Session = Depends(get_db),
    facility_id: UUID = Depends(get_facility_context),
    user: User = Depends(require_permission("claims.reconcile")),
):
    _ = user
    return list_cases(db, facility_id, status)


@router.patch("/cases/{case_id}", response_model=AnomalyCaseOut)
def anomaly_update(
    case_id: UUID,
    payload: AnomalyCaseUpdate,
    db: Session = Depends(get_db),
    facility_id: UUID = Depends(get_facility_context),
    user: User = Depends(require_permission("claims.reconcile")),
):
    try:
        return update_case(db, case_id=case_id, facility_id=facility_id, status=payload.status, note=payload.note, actor_id=user.id)
    except RevenueAnomalyError as exc:
        raise HTTPException(status_code=404 if str(exc) == "ANOMALY_CASE_NOT_FOUND" else 409, detail=str(exc)) from exc


@router.get("/cases/{case_id}/events")
def anomaly_case_events(
    case_id: UUID,
    db: Session = Depends(get_db),
    facility_id: UUID = Depends(get_facility_context),
    user: User = Depends(require_permission("claims.reconcile")),
):
    _ = user
    try:
        return case_events(db, case_id=case_id, facility_id=facility_id)
    except RevenueAnomalyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
