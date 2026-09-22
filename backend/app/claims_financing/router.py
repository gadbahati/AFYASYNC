"""Claims & Financing depth APIs."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.auth.dependencies import get_facility_context, require_permission
from app.claims_financing.service import denial_analytics, financing_pipeline, score_claim_quality
from app.database import get_db
from app.rbac.models import User

router = APIRouter(prefix="/api/v1/claims-financing", tags=["Claims Financing"])

CLAIMS_READ = "claims.read"
# Fallback permissions used across the codebase
_READ = "reports.read"


@router.get("/claims/{claim_id}/quality")
def claim_quality(
    claim_id: UUID,
    db: Session = Depends(get_db),
    facility_id: UUID = Depends(get_facility_context),
    user: User = Depends(require_permission("reports.read")),
):
    try:
        result = score_claim_quality(
            db, claim_id=claim_id, facility_id=facility_id, actor_user_id=user.id
        )
        db.commit()
        return result
    except ValueError as exc:
        code = str(exc)
        raise HTTPException(
            status_code=404 if "NOT_FOUND" in code else 403 if "ACCESS" in code else 400,
            detail=code,
        ) from exc


@router.get("/pipeline")
def pipeline(
    days: int = Query(default=30, ge=1, le=180),
    db: Session = Depends(get_db),
    facility_id: UUID = Depends(get_facility_context),
    user: User = Depends(require_permission("reports.read")),
):
    _ = user
    return financing_pipeline(db, facility_id, days=days)


@router.get("/denials")
def denials(
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
    facility_id: UUID = Depends(get_facility_context),
    user: User = Depends(require_permission("reports.read")),
):
    _ = user
    return denial_analytics(db, facility_id, limit=limit)
