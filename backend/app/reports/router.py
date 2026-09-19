from datetime import date, timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.auth.dependencies import get_facility_context, require_national_permission, require_permission
from app.database import get_db
from app.rbac.models import User
from app.reports.national_intelligence import build_national_intelligence
from app.reports.national_intelligence_schemas import NationalIntelligenceResponse
from app.reports.national_schemas import NationalOperationalSummary, NationalReport
from app.reports.national_service import build_national_report
from app.reports.schemas import FacilityOperationsReport, FacilityReport
from app.reports.service import build_facility_operations_report, build_facility_report

REPORTS_READ = "reports.read"
NATIONAL_REPORTS_READ = "reports.national.read"

router = APIRouter(prefix="/api/v1/reports", tags=["Reports"])


def _dates(start_date: date | None, end_date: date | None) -> tuple[date, date]:
    end = end_date or date.today()
    start = start_date or (end - timedelta(days=29))
    return start, end


@router.get("/facility", response_model=FacilityReport)
def facility_report(start_date: date | None = Query(default=None), end_date: date | None = Query(default=None), db: Session = Depends(get_db), facility_id: UUID = Depends(get_facility_context), user: User = Depends(require_permission(REPORTS_READ))) -> FacilityReport:
    start, end = _dates(start_date, end_date)
    try:
        return build_facility_report(db, facility_id, start, end, actor_user_id=user.id)
    except ValueError as exc:
        if str(exc) == "INVALID_REPORT_DATE_RANGE":
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        raise


@router.get("/facility/operations", response_model=FacilityOperationsReport)
def facility_operations_report(start_date: date | None = Query(default=None), end_date: date | None = Query(default=None), db: Session = Depends(get_db), facility_id: UUID = Depends(get_facility_context), user: User = Depends(require_permission(REPORTS_READ))) -> FacilityOperationsReport:
    start, end = _dates(start_date, end_date)
    try:
        return build_facility_operations_report(db, facility_id, start, end, actor_user_id=user.id)
    except ValueError as exc:
        if str(exc) == "INVALID_REPORT_DATE_RANGE":
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        raise


@router.get("/national", response_model=NationalReport)
def national_report(start_date: date | None = Query(default=None), end_date: date | None = Query(default=None), db: Session = Depends(get_db), user: User = Depends(require_national_permission(NATIONAL_REPORTS_READ))) -> NationalReport:
    start, end = _dates(start_date, end_date)
    try: return build_national_report(db, start, end, actor_user_id=user.id)
    except ValueError as exc:
        if str(exc) == "INVALID_REPORT_DATE_RANGE": raise HTTPException(status_code=400, detail=str(exc)) from exc
        raise


@router.get("/national/operations", response_model=NationalOperationalSummary)
def national_operations(db: Session = Depends(get_db), user: User = Depends(require_national_permission(NATIONAL_REPORTS_READ))) -> NationalOperationalSummary:
    report = build_national_report(db, date.today(), date.today(), actor_user_id=user.id)
    return report.operations


@router.get("/national/intelligence", response_model=NationalIntelligenceResponse)
def national_intelligence(
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
    facility_signals_page: int = Query(default=1, ge=1),
    facility_signals_page_size: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
    user: User = Depends(require_national_permission(NATIONAL_REPORTS_READ)),
) -> NationalIntelligenceResponse:
    start, end = _dates(start_date, end_date)
    try:
        return build_national_intelligence(db, start, end, actor_user_id=user.id, facility_signals_page=facility_signals_page, facility_signals_page_size=facility_signals_page_size)
    except ValueError as exc:
        if str(exc) in {"INVALID_REPORT_DATE_RANGE", "INVALID_FACILITY_SIGNALS_PAGINATION"}:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        raise
