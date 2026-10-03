from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user, get_facility_context, require_permission
from app.context.scoped_reports import build_scoped_operations_summary
from app.context.service import context_payload, scope_data_summary
from app.database import get_db
from app.rbac.models import User

router = APIRouter(prefix="/api/v1/context", tags=["context"])


@router.get("")
def context_overview(
    scope: str | None = Query(
        default=None,
        description="Optional operating scope: facility | network | county | national",
    ),
    user: User = Depends(get_current_user),
    facility_id: UUID = Depends(get_facility_context),
    db: Session = Depends(get_db),
):
    """Authorization profile + allowed workspaces + active data scope."""
    return context_payload(db, user=user, facility_id=facility_id, scope=scope)


@router.get("/scope-summary")
def operating_scope_summary(
    scope: str = Query(default="facility", description="facility | network | county | national"),
    user: User = Depends(get_current_user),
    facility_id: UUID = Depends(get_facility_context),
    db: Session = Depends(get_db),
):
    """Facility set + basic counts for the selected operating scope."""
    return scope_data_summary(db, user=user, token_facility_id=facility_id, scope=scope)


@router.get("/operations-summary")
def scoped_operations_summary(
    scope: str = Query(default="facility", description="facility | network | county | national"),
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
    user: User = Depends(require_permission("reports.read")),
    facility_id: UUID = Depends(get_facility_context),
    db: Session = Depends(get_db),
):
    """Phase 91 — multi-facility operational aggregates under authorized scope.

    Requires reports.read. Scope expansion is still constrained by RBAC:
    ordinary staff get facility/network only; county/national need admin.
    """
    try:
        return build_scoped_operations_summary(
            db,
            user=user,
            token_facility_id=facility_id,
            scope=scope,
            start_date=start_date,
            end_date=end_date,
        )
    except ValueError as exc:
        if str(exc) == "INVALID_REPORT_DATE_RANGE":
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        raise
