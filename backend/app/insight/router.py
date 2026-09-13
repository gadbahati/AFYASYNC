from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.dependencies import get_facility_context, require_permission
from app.database import get_db
from app.insight.schemas import (
    CommandCentreResponse,
    CoverageSimulateRequest,
    CoverageSimulateResponse,
    FraudRadarResponse,
)
from app.insight.service import build_command_centre, scan_fraud_signals, simulate_coverage
from app.rbac.models import User

INSIGHT_READ = "reports.read"

router = APIRouter(prefix="/api/v1/insight", tags=["Insight"])


@router.post("/coverage/simulate", response_model=CoverageSimulateResponse)
def coverage_simulate(
    payload: CoverageSimulateRequest,
    db: Session = Depends(get_db),
    facility_id: UUID = Depends(get_facility_context),
    user: User = Depends(require_permission(INSIGHT_READ)),
) -> CoverageSimulateResponse:
    _ = user
    return simulate_coverage(db, facility_id, payload)


@router.get("/command-centre", response_model=CommandCentreResponse)
def command_centre(
    db: Session = Depends(get_db),
    facility_id: UUID = Depends(get_facility_context),
    user: User = Depends(require_permission(INSIGHT_READ)),
) -> CommandCentreResponse:
    _ = user
    return build_command_centre(db, facility_id)


@router.get("/fraud-radar", response_model=FraudRadarResponse)
def fraud_radar(
    db: Session = Depends(get_db),
    facility_id: UUID = Depends(get_facility_context),
    user: User = Depends(require_permission(INSIGHT_READ)),
) -> FraudRadarResponse:
    _ = user
    return scan_fraud_signals(db, facility_id)
