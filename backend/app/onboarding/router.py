"""Facility onboarding & migration kit APIs."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth.dependencies import get_facility_context, require_permission
from app.database import get_db
from app.onboarding.service import facility_onboarding_kit, migration_playbook
from app.rbac.models import User

router = APIRouter(prefix="/api/v1/onboarding", tags=["Onboarding"])


@router.get("/facility-kit")
def facility_kit(
    db: Session = Depends(get_db),
    facility_id: UUID = Depends(get_facility_context),
    user: User = Depends(require_permission("reports.read")),
):
    _ = user
    try:
        return facility_onboarding_kit(db, facility_id=facility_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.get("/migration-playbook")
def playbook(
    user: User = Depends(require_permission("reports.read")),
):
    _ = user
    return migration_playbook()
