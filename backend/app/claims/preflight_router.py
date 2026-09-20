from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.auth.dependencies import get_facility_context, require_permission
from app.claims.permissions import CLAIMS_VALIDATE
from app.claims.preflight_schemas import ClaimPreflightResponse, FacilityKesAtRiskResponse
from app.claims.preflight_service import preflight_claim
from app.claims.risk_service import facility_kes_at_risk
from app.claims.service import ClaimsError
from app.database import get_db
from app.rbac.models import User

router = APIRouter(prefix="/api/v1/claims", tags=["Claims"])


@router.get("/invoices/{invoice_id}/preflight", response_model=ClaimPreflightResponse)
def claim_preflight(
    invoice_id: UUID,
    db: Session = Depends(get_db),
    facility_id: UUID = Depends(get_facility_context),
    user: User = Depends(require_permission(CLAIMS_VALIDATE)),
) -> ClaimPreflightResponse:
    try:
        return preflight_claim(
            db,
            invoice_id=invoice_id,
            facility_id=facility_id,
            actor_user_id=user.id,
        )
    except ClaimsError as exc:
        code = str(exc)
        status_code = (
            404
            if code == "INVOICE_NOT_FOUND"
            else 403
            if code == "FACILITY_ACCESS_DENIED"
            else 400
        )
        raise HTTPException(status_code=status_code, detail=code) from exc


@router.get("/risk/kes-at-risk", response_model=FacilityKesAtRiskResponse)
def claims_kes_at_risk(
    days: int = Query(default=7, ge=1, le=90),
    db: Session = Depends(get_db),
    facility_id: UUID = Depends(get_facility_context),
    user: User = Depends(require_permission(CLAIMS_VALIDATE)),
) -> FacilityKesAtRiskResponse:
    """Facility dashboard: rejected + in-flight claim value in the window."""
    _ = user
    data = facility_kes_at_risk(db, facility_id=facility_id, days=days)
    return FacilityKesAtRiskResponse(**data)
