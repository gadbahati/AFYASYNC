"""National logistics depth APIs."""

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.auth.dependencies import get_facility_context, require_permission
from app.database import get_db
from app.logistics.service import facility_supply_health, redistribution_suggestions, stockout_board
from app.rbac.models import User

router = APIRouter(prefix="/api/v1/logistics", tags=["Logistics"])


@router.get("/stockout-board")
def get_stockout_board(
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("reports.read")),
    county: str | None = Query(default=None, max_length=80),
    limit: int = Query(default=100, ge=1, le=300),
):
    _ = user
    return stockout_board(db, county=county, limit=limit)


@router.get("/redistribution")
def get_redistribution(
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("reports.read")),
    county: str | None = Query(default=None, max_length=80),
    limit: int = Query(default=50, ge=1, le=100),
):
    _ = user
    return redistribution_suggestions(db, county=county, limit=limit)


@router.get("/facility-health")
def get_facility_health(
    db: Session = Depends(get_db),
    facility_id: UUID = Depends(get_facility_context),
    user: User = Depends(require_permission("reports.read")),
):
    _ = user
    return facility_supply_health(db, facility_id=facility_id)
