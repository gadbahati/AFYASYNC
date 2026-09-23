"""Pilot evidence pack & county handover APIs."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.auth.dependencies import require_permission
from app.database import get_db
from app.pilot_handover.service import county_handover_pack, pilot_evidence_pack
from app.rbac.models import User

router = APIRouter(prefix="/api/v1/pilot-handover", tags=["PilotHandover"])


@router.get("/evidence-pack")
def evidence_pack(
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("reports.read")),
    county: str | None = Query(default=None, max_length=80),
    facility_id: UUID | None = Query(default=None),
):
    _ = user
    return pilot_evidence_pack(db, county=county, facility_id=facility_id)


@router.get("/county-handover")
def county_handover(
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("reports.read")),
    county: str = Query(..., min_length=2, max_length=80),
):
    _ = user
    try:
        return county_handover_pack(db, county=county)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
