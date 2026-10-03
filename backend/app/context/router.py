from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user, get_facility_context
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
    """Prove that operating context changes data, not only navigation.

    Returns the facility set authorized under the selected scope and aggregate
    counts (patients, encounters, claims) limited to that set.
    """
    return scope_data_summary(
        db, user=user, token_facility_id=facility_id, scope=scope
    )
