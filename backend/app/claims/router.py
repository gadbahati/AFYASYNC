from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user, get_facility_context, require_permission
from app.claims.models import Claim
from app.claims.permissions import CLAIMS_CREATE, CLAIMS_RECONCILE, CLAIMS_SUBMIT, CLAIMS_VALIDATE
from app.claims.schemas import ClaimCreate, ClaimResponseOut, ClaimSubmitOut, ClaimValidationOut, ReconcileCreate, ReconcileResponse
from app.claims.service import ClaimsError, create_claim, reconcile_claim, submit_claim, validate_claim
from app.database import get_db
from app.rbac.models import Staff, User

router = APIRouter(prefix="/api/v1/claims", tags=["Claims"])


def _error(exc: ClaimsError) -> HTTPException:
    mapping = {"INVOICE_NOT_FOUND": 404, "ENCOUNTER_NOT_FOUND": 404, "CLAIM_NOT_FOUND": 404, "CHARGE_NOT_FOUND": 404, "FACILITY_ACCESS_DENIED": 403, "CLAIM_ALREADY_EXISTS": 409, "CLAIM_ALREADY_RECONCILED": 409, "CLAIM_NOT_READY": 409, "VERIFIED_COVERAGE_REQUIRED": 409, "PAYER_NOT_ACTIVE": 409}
    return HTTPException(status_code=mapping.get(str(exc), 400), detail=str(exc))


@router.post("", response_model=ClaimResponseOut, status_code=201)
def create(payload: ClaimCreate, db: Session = Depends(get_db), facility_id: UUID = Depends(get_facility_context), _: User = Depends(require_permission(CLAIMS_CREATE))):
    try:
        return create_claim(db, facility_id, payload.invoice_id)
    except ClaimsError as exc:
        raise _error(exc) from exc


@router.post("/{claim_id}/validate", response_model=ClaimValidationOut)
def validate(claim_id: UUID, db: Session = Depends(get_db), facility_id: UUID = Depends(get_facility_context), _: User = Depends(require_permission(CLAIMS_VALIDATE))):
    try:
        errors = validate_claim(db, claim_id, facility_id)
        claim = db.get(Claim, claim_id)
        return ClaimValidationOut(claim_id=claim_id, valid=not errors, errors=errors)
    except ClaimsError as exc:
        raise _error(exc) from exc


@router.post("/{claim_id}/submit", response_model=ClaimSubmitOut)
def submit(claim_id: UUID, db: Session = Depends(get_db), facility_id: UUID = Depends(get_facility_context), _: User = Depends(require_permission(CLAIMS_SUBMIT))):
    try:
        claim = submit_claim(db, claim_id, facility_id)
        return ClaimSubmitOut(claim_id=claim.id, status=claim.status, message="Claim queued for authorised payer submission")
    except ClaimsError as exc:
        raise _error(exc) from exc


@router.post("/{claim_id}/reconcile", response_model=ReconcileResponse)
def reconcile(claim_id: UUID, payload: ReconcileCreate, db: Session = Depends(get_db), facility_id: UUID = Depends(get_facility_context), user: User = Depends(require_permission(CLAIMS_RECONCILE))):
    staff = db.scalar(__import__("sqlalchemy").select(Staff).where(Staff.person_id == user.person_id, Staff.facility_id == facility_id, Staff.status == "ACTIVE").limit(1))
    if staff is None:
        raise HTTPException(status_code=403, detail="FACILITY_ACCESS_DENIED")
    try:
        reconciliation = reconcile_claim(db, claim_id, facility_id, staff.id, payload.received_amount)
        return ReconcileResponse(claim_id=reconciliation.claim_id, expected_amount=reconciliation.expected_amount, received_amount=reconciliation.received_amount, difference=reconciliation.difference, status=reconciliation.status)
    except ClaimsError as exc:
        raise _error(exc) from exc
