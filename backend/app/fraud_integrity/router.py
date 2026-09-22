"""Claims integrity / fraud signal APIs."""

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.auth.dependencies import get_facility_context, require_permission
from app.database import get_db
from app.fraud_integrity.service import facility_integrity_scan, national_integrity_overview
from app.rbac.models import User

router = APIRouter(prefix="/api/v1/fraud-integrity", tags=["Fraud Integrity"])


@router.get("/facility-scan")
def facility_scan(
    db: Session = Depends(get_db),
    facility_id: UUID = Depends(get_facility_context),
    user: User = Depends(require_permission("reports.read")),
    days: int = Query(default=30, ge=7, le=90),
):
    _ = user
    return facility_integrity_scan(db, facility_id=facility_id, days=days)


@router.get("/national-overview")
def national_overview(
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("reports.read")),
    days: int = Query(default=30, ge=7, le=90),
    limit: int = Query(default=30, ge=1, le=100),
):
    _ = user
    return national_integrity_overview(db, days=days, limit=limit)
