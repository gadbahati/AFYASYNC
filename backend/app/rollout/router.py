"""Pilot evidence & county rollout APIs."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.auth.dependencies import get_facility_context, require_permission
from app.database import get_db
from app.rbac.models import User
from app.rollout.service import county_rollout_dashboard, pilot_evidence_pack

router = APIRouter(prefix="/api/v1/rollout", tags=["Rollout"])


@router.get("/county-dashboard")
def county_dashboard(
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("reports.read")),
    limit: int = Query(default=50, ge=1, le=100),
):
    _ = user
    return county_rollout_dashboard(db, limit_counties=limit)


@router.get("/pilot-evidence")
def pilot_evidence(
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("reports.read")),
    include_facility: bool = Query(default=False),
    facility_id: UUID | None = Depends(get_facility_context),
):
    _ = user
    try:
        return pilot_evidence_pack(
            db,
            facility_id=facility_id if include_facility else None,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
