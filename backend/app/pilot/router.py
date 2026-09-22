"""Pilot operations & evidence pack APIs."""

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.dependencies import get_facility_context, require_permission
from app.database import get_db
from app.pilot.checklist import pilot_checklist_template
from app.pilot.evidence import build_evidence_pack
from app.pilot.migration import migration_readiness
from app.rbac.models import User

router = APIRouter(prefix="/api/v1/pilot", tags=["Pilot Operations"])


@router.get("/checklist")
def checklist(
    user: User = Depends(require_permission("reports.read")),
):
    _ = user
    return pilot_checklist_template()


@router.get("/migration-readiness")
def migration(
    db: Session = Depends(get_db),
    facility_id: UUID = Depends(get_facility_context),
    user: User = Depends(require_permission("reports.read")),
):
    _ = user
    return migration_readiness(db, facility_id=facility_id)


@router.get("/evidence-pack")
def evidence_pack(
    db: Session = Depends(get_db),
    facility_id: UUID = Depends(get_facility_context),
    user: User = Depends(require_permission("reports.read")),
):
    _ = user
    return build_evidence_pack(db, facility_id=facility_id)
