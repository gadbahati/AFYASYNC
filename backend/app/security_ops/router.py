"""Security posture, privacy ops & access review APIs."""

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.auth.dependencies import get_facility_context, require_permission
from app.database import get_db
from app.rbac.models import User
from app.security_ops.service import access_review, live_security_checklist, privacy_ops_summary

router = APIRouter(prefix="/api/v1/security-ops", tags=["Security Ops"])


@router.get("/access-review")
def get_access_review(
    db: Session = Depends(get_db),
    facility_id: UUID = Depends(get_facility_context),
    user: User = Depends(require_permission("reports.read")),
    days: int = Query(default=7, ge=1, le=90),
    limit: int = Query(default=100, ge=1, le=300),
):
    _ = user
    return access_review(db, facility_id=facility_id, days=days, limit=limit)


@router.get("/privacy-summary")
def get_privacy_summary(
    db: Session = Depends(get_db),
    facility_id: UUID = Depends(get_facility_context),
    user: User = Depends(require_permission("reports.read")),
    days: int = Query(default=30, ge=1, le=90),
):
    _ = user
    return privacy_ops_summary(db, facility_id=facility_id, days=days)


@router.get("/checklist")
def get_checklist(
    user: User = Depends(require_permission("reports.read")),
):
    _ = user
    return live_security_checklist()
