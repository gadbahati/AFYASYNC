"""Certification evidence & security posture APIs (National Phase 11)."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth.dependencies import get_facility_context, require_permission
from app.certification.checklist import CERTIFICATION_DOMAINS, summarise_checklist
from app.certification.privacy_service import build_privacy_package
from app.certification.security_posture import security_posture
from app.database import get_db
from app.rbac.models import User

router = APIRouter(prefix="/api/v1/certification", tags=["Certification"])


@router.get("/evidence")
def evidence_pack():
    """Full DHA-style evidence catalogue for auditors."""
    summary = summarise_checklist()
    return {
        "program": "AFYASYNC_NATIONAL_REPLACEMENT",
        "phase": 11,
        "summary": summary,
        "domains": CERTIFICATION_DOMAINS,
        "developer": "BAHATI GAD WANGWE",
    }


@router.get("/security-posture")
def posture(
    user: User = Depends(require_permission("reports.read")),
):
    _ = user
    return security_posture()


@router.get("/privacy-package/{person_id}")
def privacy_package(
    person_id: UUID,
    db: Session = Depends(get_db),
    facility_id: UUID = Depends(get_facility_context),
    user: User = Depends(require_permission("patients.record.read")),
):
    _ = facility_id, user
    try:
        return build_privacy_package(db, person_id=person_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
