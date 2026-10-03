from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user, get_facility_context
from app.database import get_db
from app.rbac.models import User

router = APIRouter(prefix="/api/v1/context", tags=["context"])

@router.get("")
def context_overview(
    user: User = Depends(get_current_user),
    facility_id = Depends(get_facility_context),
    db: Session = Depends(get_db),
):
    from app.auth.dependencies import _is_system_administrator
    is_admin = _is_system_administrator(db, user)
    scopes = ["facility"]
    if is_admin:
        scopes = ["facility", "network", "county", "national"]
    return {
        "current": {"scope": "facility", "facility_id": str(facility_id)},
        "available_scopes": scopes,
        "context_model": {
            "facility": "Operational scope for one authorized facility.",
            "network": "Aggregated scope for an authorized provider network.",
            "county": "County health-management scope when explicitly authorized.",
            "national": "National scope reserved for explicitly authorized platform/government operations.",
        },
    }
