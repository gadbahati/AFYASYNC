from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user, get_facility_context, require_permission
from app.context.scoped_reports import build_scoped_operations_summary
from app.context.scoped_surface import scoped_surface_manifest
from app.context.service import context_payload, record_scope_selection, scope_data_summary
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


@router.get("/scoped-surface")
def scoped_surface(
    user: User = Depends(get_current_user),
):
    """Phase 98 — inventory of scope-aware reads for ops/DHA evidence (auth required)."""
    _ = user
    return scoped_surface_manifest()


@router.get("/scope-summary")
def operating_scope_summary(
    scope: str = Query(default="facility", description="facility | network | county | national"),
    user: User = Depends(get_current_user),
    facility_id: UUID = Depends(get_facility_context),
    db: Session = Depends(get_db),
):
    """Facility set + basic counts for the selected operating scope."""
    return scope_data_summary(db, user=user, token_facility_id=facility_id, scope=scope)


@router.post("/scope")
def set_operating_scope(
    scope: str = Query(..., description="facility | network | county | national"),
    previous_scope: str | None = Query(default=None),
    user: User = Depends(get_current_user),
    facility_id: UUID = Depends(get_facility_context),
    db: Session = Depends(get_db),
):
    """Phase 95 — auditable operating-scope change."""
    return record_scope_selection(
        db,
        user=user,
        facility_id=facility_id,
        scope=scope,
        previous_scope=previous_scope,
    )


@router.get("/operations-summary")
def scoped_operations_summary(
    scope: str = Query(default="facility", description="facility | network | county | national"),
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
    user: User = Depends(require_permission("reports.read")),
    facility_id: UUID = Depends(get_facility_context),
    db: Session = Depends(get_db),
):
    """Phase 91 — multi-facility operational aggregates under authorized scope."""
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
