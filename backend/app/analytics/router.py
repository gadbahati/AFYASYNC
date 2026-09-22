"""Analytics, fraud & public-health reporting routes."""

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.analytics.claims_kpis import claims_kpis
from app.analytics.fraud_service import scan_facility_fraud
from app.analytics.public_health import public_health_summary
from app.auth.dependencies import get_facility_context, require_permission
from app.database import get_db
from app.rbac.models import User

router = APIRouter(prefix="/api/v1/analytics", tags=["Analytics"])


@router.get("/fraud/facility")
def fraud_facility(
    db: Session = Depends(get_db),
    facility_id: UUID = Depends(get_facility_context),
    user: User = Depends(require_permission("reports.read")),
    days: int = Query(default=30, ge=1, le=365),
):
    _ = user
    return scan_facility_fraud(db, facility_id=facility_id, days=days)


@router.get("/public-health/facility")
def public_health_facility(
    db: Session = Depends(get_db),
    facility_id: UUID = Depends(get_facility_context),
    user: User = Depends(require_permission("reports.read")),
    days: int = Query(default=30, ge=1, le=365),
):
    _ = user
    return public_health_summary(db, facility_id=facility_id, days=days)


@router.get("/claims/kpis")
def claims_kpi_endpoint(
    db: Session = Depends(get_db),
    facility_id: UUID = Depends(get_facility_context),
    user: User = Depends(require_permission("reports.read")),
    days: int = Query(default=30, ge=1, le=365),
):
    _ = user
    return claims_kpis(db, facility_id=facility_id, days=days)


@router.get("/overview")
def analytics_overview(
    db: Session = Depends(get_db),
    facility_id: UUID = Depends(get_facility_context),
    user: User = Depends(require_permission("reports.read")),
    days: int = Query(default=30, ge=1, le=365),
):
    _ = user
    fraud = scan_facility_fraud(db, facility_id=facility_id, days=days)
    ph = public_health_summary(db, facility_id=facility_id, days=days)
    kpis = claims_kpis(db, facility_id=facility_id, days=days)
    return {
        "facility_id": str(facility_id),
        "window_days": days,
        "fraud_summary": fraud["summary"],
        "fraud_high": fraud["high"],
        "claims_total": kpis["claims_total"],
        "denial_rate": kpis["denial_rate"],
        "encounters_by_status": ph["encounters_by_status"],
        "top_diagnosis_codes": ph["top_diagnosis_codes"][:10],
        "developer": "BAHATI GAD WANGWE",
    }
