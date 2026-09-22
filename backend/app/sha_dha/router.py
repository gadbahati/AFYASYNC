"""SHA / DHA AfyaLink integration routes."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth.dependencies import get_facility_context, require_permission
from app.database import get_db
from app.rbac.models import User
from app.sha_dha.service import connection_status, poll_claim_status, run_eligibility, submit_local_claim

router = APIRouter(prefix="/api/v1/sha-dha", tags=["SHA DHA AfyaLink"])


class EligibilityBody(BaseModel):
    membership_number: str = Field(min_length=3, max_length=80)
    national_id: str | None = Field(default=None, max_length=30)


@router.get("/status")
def integration_status():
    """Whether live AfyaLink credentials are configured."""
    return connection_status()


@router.post("/eligibility")
def eligibility(
    body: EligibilityBody,
    db: Session = Depends(get_db),
    facility_id: UUID = Depends(get_facility_context),
    user: User = Depends(require_permission("patients.record.read")),
):
    try:
        result = run_eligibility(
            db,
            membership_number=body.membership_number,
            facility_id=facility_id,
            actor_user_id=user.id,
            national_id=body.national_id,
        )
        db.commit()
        return result
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/claims/{claim_id}/submit")
def submit_claim(
    claim_id: UUID,
    db: Session = Depends(get_db),
    facility_id: UUID = Depends(get_facility_context),
    user: User = Depends(require_permission("claims.write")),
):
    try:
        result = submit_local_claim(
            db, claim_id=claim_id, facility_id=facility_id, actor_user_id=user.id
        )
        db.commit()
        return result
    except ValueError as exc:
        code = str(exc)
        status = 404 if "NOT_FOUND" in code else 403 if "ACCESS" in code else 400
        # claims.write may not exist on all installs — try softer permission path
        raise HTTPException(status_code=status, detail=code) from exc


@router.get("/claims/status")
def claim_status(
    bundle_id: str = Query(min_length=4, max_length=120),
    db: Session = Depends(get_db),
    facility_id: UUID = Depends(get_facility_context),
    user: User = Depends(require_permission("reports.read")),
):
    try:
        result = poll_claim_status(
            db, bundle_id=bundle_id, facility_id=facility_id, actor_user_id=user.id
        )
        db.commit()
        return result
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
