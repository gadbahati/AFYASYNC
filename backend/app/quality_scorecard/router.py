"""Quality KPI scorecard APIs."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.auth.dependencies import get_facility_context, require_permission
from app.database import get_db
from app.quality_scorecard.service import facility_scorecard, national_scorecard
from app.rbac.models import User

router = APIRouter(prefix="/api/v1/quality", tags=["Quality Scorecard"])


@router.get("/facility-scorecard")
def get_facility_scorecard(
    db: Session = Depends(get_db),
    facility_id: UUID = Depends(get_facility_context),
    user: User = Depends(require_permission("reports.read")),
    days: int = Query(default=30, ge=7, le=90),
):
    _ = user
    try:
        return facility_scorecard(db, facility_id=facility_id, days=days)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.get("/national-scorecard")
def get_national_scorecard(
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("reports.read")),
    days: int = Query(default=30, ge=7, le=90),
    limit: int = Query(default=50, ge=1, le=100),
):
    _ = user
    return national_scorecard(db, days=days, limit=limit)
