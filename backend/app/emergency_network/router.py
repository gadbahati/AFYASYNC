"""Emergency & referral network depth APIs."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.auth.dependencies import get_facility_context, require_permission
from app.database import get_db
from app.emergency_network.service import (
    emergency_board,
    facility_emergency_load,
    network_overview,
    referral_destinations,
)
from app.rbac.models import User

router = APIRouter(prefix="/api/v1/emergency-network", tags=["Emergency Network"])


@router.get("/board")
def board(
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("reports.read")),
    county: str | None = Query(default=None, max_length=80),
    limit: int = Query(default=100, ge=1, le=200),
):
    _ = user
    return emergency_board(db, county=county, limit=limit)


@router.get("/facility-load")
def facility_load(
    db: Session = Depends(get_db),
    facility_id: UUID = Depends(get_facility_context),
    user: User = Depends(require_permission("reports.read")),
):
    _ = user
    return facility_emergency_load(db, facility_id=facility_id)


@router.get("/referral-destinations")
def destinations(
    db: Session = Depends(get_db),
    facility_id: UUID = Depends(get_facility_context),
    user: User = Depends(require_permission("reports.read")),
    preferred_county: str | None = Query(default=None, max_length=80),
    limit: int = Query(default=20, ge=1, le=50),
):
    _ = user
    try:
        return referral_destinations(
            db,
            source_facility_id=facility_id,
            preferred_county=preferred_county,
            limit=limit,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/overview")
def overview(
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("reports.read")),
    days: int = Query(default=7, ge=1, le=90),
):
    _ = user
    return network_overview(db, days=days)
