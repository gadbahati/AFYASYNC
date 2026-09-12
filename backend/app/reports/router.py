from datetime import date, timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.auth.dependencies import get_facility_context, require_permission
from app.database import get_db
from app.rbac.models import User
from app.reports.schemas import FacilityReport
from app.reports.service import build_facility_report

REPORTS_READ = "reports.read"

router = APIRouter(prefix="/api/v1/reports", tags=["Reports"])


@router.get("/facility", response_model=FacilityReport)
def facility_report(
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
    db: Session = Depends(get_db),
    facility_id: UUID = Depends(get_facility_context),
    user: User = Depends(require_permission(REPORTS_READ)),
) -> FacilityReport:
    end = end_date or date.today()
    start = start_date or (end - timedelta(days=29))
    try:
        return build_facility_report(db, facility_id, start, end, actor_user_id=user.id)
    except ValueError as exc:
        if str(exc) == "INVALID_REPORT_DATE_RANGE":
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        raise
