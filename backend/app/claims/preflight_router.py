from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth.dependencies import get_facility_context, require_permission
from app.claims.permissions import CLAIMS_VALIDATE
from app.claims.preflight_schemas import ClaimPreflightResponse
from app.claims.preflight_service import preflight_claim
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
        status_code = 404 if code == "INVOICE_NOT_FOUND" else 403 if code == "FACILITY_ACCESS_DENIED" else 400
        raise HTTPException(status_code=status_code, detail=code) from exc
