from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.dependencies import get_facility_context, require_permission
from app.billing.models import Invoice
from app.claims.models import Claim, ClaimResponse
from app.claims.permissions import CLAIMS_CREATE, CLAIMS_RECONCILE, CLAIMS_SUBMIT, CLAIMS_VALIDATE
from app.claims.rejection_guide import guide_for
from app.claims.schemas import ClaimCreate, ClaimResponseOut, ClaimSubmitOut, ClaimValidationOut, PayerResponseCreate, ReconcileCreate, ReconcileResponse
from app.claims.service import ClaimsError, create_claim, record_payer_response, reconcile_claim, submit_claim, validate_claim
from app.config import settings
from app.database import get_db
from app.rbac.models import Staff, User

router = APIRouter(prefix="/api/v1/claims", tags=["Claims"])


class RejectionWorkbenchItem(BaseModel):
    claim_id: UUID
    claim_number: str
    invoice_id: UUID
    status: str
    claim_amount: float
    response_code: str | None = None
    response_message: str | None = None
    guide_code: str
    guide_title: str
    guide_fix: str
    guide_owner: str


class SandboxRejectRequest(BaseModel):
    response_code: str = Field(default="COV001", max_length=80)
    response_message: str = Field(default="Coverage not verified (sandbox)", max_length=500)
    external_reference: str | None = Field(default="SANDBOX-REJECT", max_length=150)


def _error(exc: ClaimsError) -> HTTPException:
    mapping = {
        "INVOICE_NOT_FOUND": 404, "ENCOUNTER_NOT_FOUND": 404, "ENCOUNTER_MISMATCH": 409,
        "CLAIM_NOT_FOUND": 404, "CHARGE_NOT_FOUND": 404, "SERVICE_NOT_FOUND": 404,
        "FACILITY_ACCESS_DENIED": 403, "CLAIM_ALREADY_EXISTS": 409, "CLAIM_ALREADY_RECONCILED": 409,
        "CLAIM_NOT_READY": 409, "CLAIM_NOT_VALIDATABLE": 409, "CLAIM_NOT_RECONCILABLE": 409,
        "VERIFIED_COVERAGE_REQUIRED": 409, "PAYER_NOT_ACTIVE": 409, "PAYER_COVERAGE_REQUIRED": 409,
        "CLAIM_ITEMS_REQUIRED": 409, "CLAIM_RESPONSE_NOT_ALLOWED": 409,
        "INVALID_CLAIM_RESPONSE_STATUS": 400, "INVALID_APPROVED_AMOUNT": 400,
        "APPROVED_AMOUNT_EXCEEDS_CLAIM": 400, "APPROVED_AMOUNT_REQUIRED": 400,
        "INVALID_RECEIVED_AMOUNT": 400, "RECEIVED_AMOUNT_EXCEEDS_EXPECTED": 400,
        "INVOICE_VOID": 409, "CLAIM_AMOUNT_INVALID": 400, "CLAIM_INVOICE_TOTAL_MISMATCH": 409,
        "CLAIM_ITEM_TOTAL_MISMATCH": 409, "DUPLICATE_PAYER_RESPONSE": 409,
        "PAYER_INTEGRATION_NOT_CONFIGURED": 409, "CLAIM_REVALIDATION_FAILED": 409,
        "INTEGRATION_NOT_FOUND": 404, "INTEGRATION_NOT_ACTIVE": 409,
        "CASH_ENCOUNTER_NO_CLAIM": 409, "SHA_MODE_REQUIRES_SHA_PAYER": 409, "AFYASYNC_MODE_REQUIRES_AFYASYNC_PAYER": 409,
    }
    return HTTPException(status_code=mapping.get(str(exc), 400), detail=str(exc))


@router.get("", response_model=list[ClaimResponseOut])
def list_claims(limit: int = Query(default=50, ge=1, le=100), db: Session = Depends(get_db), facility_id: UUID = Depends(get_facility_context), user: User = Depends(require_permission(CLAIMS_CREATE))):
    _ = user
    return list(db.scalars(select(Claim).join(Invoice, Invoice.id == Claim.invoice_id).where(Invoice.facility_id == facility_id).order_by(Claim.updated_at.desc()).limit(limit)).all())


@router.get("/workbench/rejections", response_model=list[RejectionWorkbenchItem])
def rejection_workbench(limit: int = Query(default=50, ge=1, le=100), db: Session = Depends(get_db), facility_id: UUID = Depends(get_facility_context), user: User = Depends(require_permission(CLAIMS_VALIDATE))):
    _ = user
    claims = list(db.scalars(select(Claim).join(Invoice, Invoice.id == Claim.invoice_id).where(Invoice.facility_id == facility_id, Claim.status == "REJECTED").order_by(Claim.updated_at.desc()).limit(limit)).all())
    out: list[RejectionWorkbenchItem] = []
    for claim in claims:
        last = db.scalar(select(ClaimResponse).where(ClaimResponse.claim_id == claim.id).order_by(ClaimResponse.received_at.desc()).limit(1))
        code = last.response_code if last else None
        msg = last.response_message if last else None
        g = guide_for(code, msg)
        out.append(RejectionWorkbenchItem(claim_id=claim.id, claim_number=claim.claim_id, invoice_id=claim.invoice_id, status=claim.status, claim_amount=float(claim.claim_amount), response_code=code, response_message=msg, guide_code=g["code"], guide_title=g["title"], guide_fix=g["fix"], guide_owner=g["owner"]))
    return out


@router.get("/{claim_id}/rejection-guide")
def claim_rejection_guide(claim_id: UUID, db: Session = Depends(get_db), facility_id: UUID = Depends(get_facility_context), user: User = Depends(require_permission(CLAIMS_VALIDATE))):
    _ = user
    claim = db.get(Claim, claim_id)
    if claim is None:
        raise HTTPException(status_code=404, detail="CLAIM_NOT_FOUND")
    invoice = db.get(Invoice, claim.invoice_id)
    if invoice is None or invoice.facility_id != facility_id:
        raise HTTPException(status_code=403, detail="FACILITY_ACCESS_DENIED")
    last = db.scalar(select(ClaimResponse).where(ClaimResponse.claim_id == claim.id).order_by(ClaimResponse.received_at.desc()).limit(1))
    g = guide_for(last.response_code if last else None, last.response_message if last else None)
    return {"claim_id": claim.id, "claim_number": claim.claim_id, "status": claim.status, "last_response": {"code": last.response_code if last else None, "message": last.response_message if last else None, "status": last.status if last else None}, "guide": g}


@router.post("/{claim_id}/resubmit", response_model=ClaimSubmitOut)
def resubmit_claim(claim_id: UUID, db: Session = Depends(get_db), facility_id: UUID = Depends(get_facility_context), user: User = Depends(require_permission(CLAIMS_SUBMIT))):
    """Re-validate a rejected claim and queue it again only when validation passes."""
    try:
        errors = validate_claim(db, claim_id, facility_id, actor_user_id=user.id)
        if errors:
            raise ClaimsError("CLAIM_REVALIDATION_FAILED")
        claim = submit_claim(db, claim_id, facility_id, actor_user_id=user.id)
        return ClaimSubmitOut(claim_id=claim.id, status=claim.status, message="Claim revalidated and queued for authorised payer submission")
    except ClaimsError as exc:
        raise _error(exc) from exc


@router.post("/{claim_id}/sandbox-reject", response_model=ClaimResponseOut)
def sandbox_reject(claim_id: UUID, payload: SandboxRejectRequest, db: Session = Depends(get_db), facility_id: UUID = Depends(get_facility_context), user: User = Depends(require_permission(CLAIMS_VALIDATE))):
    """Development-only payer rejection simulation; never available in production."""
    if settings.environment == "production":
        raise HTTPException(status_code=404, detail="NOT_FOUND")
    try:
        claim = db.get(Claim, claim_id)
        if claim is None:
            raise ClaimsError("CLAIM_NOT_FOUND")
        invoice = db.get(Invoice, claim.invoice_id)
        if invoice is None or invoice.facility_id != facility_id:
            raise ClaimsError("FACILITY_ACCESS_DENIED")
        if claim.status == "READY":
            claim.status = "SUBMITTED"
            db.flush()
        return record_payer_response(db, claim_id, facility_id, "REJECTED", payload.response_code, payload.response_message, payload.external_reference or f"SANDBOX-{claim.claim_id}", None, actor_user_id=user.id)
    except ClaimsError as exc:
        raise _error(exc) from exc


@router.post("", response_model=ClaimResponseOut, status_code=201)
def create(payload: ClaimCreate, db: Session = Depends(get_db), facility_id: UUID = Depends(get_facility_context), user: User = Depends(require_permission(CLAIMS_CREATE))):
    try:
        return create_claim(db, facility_id, payload.invoice_id, actor_user_id=user.id)
    except ClaimsError as exc:
        raise _error(exc) from exc


@router.post("/{claim_id}/validate", response_model=ClaimValidationOut)
def validate(claim_id: UUID, db: Session = Depends(get_db), facility_id: UUID = Depends(get_facility_context), user: User = Depends(require_permission(CLAIMS_VALIDATE))):
    try:
        errors = validate_claim(db, claim_id, facility_id, actor_user_id=user.id)
        return ClaimValidationOut(claim_id=claim_id, valid=not errors, errors=errors)
    except ClaimsError as exc:
        raise _error(exc) from exc


@router.post("/{claim_id}/submit", response_model=ClaimSubmitOut)
def submit(claim_id: UUID, db: Session = Depends(get_db), facility_id: UUID = Depends(get_facility_context), user: User = Depends(require_permission(CLAIMS_SUBMIT))):
    try:
        claim = submit_claim(db, claim_id, facility_id, actor_user_id=user.id)
        return ClaimSubmitOut(claim_id=claim.id, status=claim.status, message="Claim queued for authorised payer submission")
    except ClaimsError as exc:
        raise _error(exc) from exc


@router.post("/{claim_id}/response", response_model=ClaimResponseOut)
def payer_response(claim_id: UUID, payload: PayerResponseCreate, db: Session = Depends(get_db), facility_id: UUID = Depends(get_facility_context), user: User = Depends(require_permission(CLAIMS_VALIDATE))):
    try:
        return record_payer_response(db, claim_id, facility_id, payload.status, payload.response_code, payload.response_message, payload.external_reference, payload.approved_amount, actor_user_id=user.id)
    except ClaimsError as exc:
        raise _error(exc) from exc


@router.post("/{claim_id}/reconcile", response_model=ReconcileResponse)
def reconcile(claim_id: UUID, payload: ReconcileCreate, db: Session = Depends(get_db), facility_id: UUID = Depends(get_facility_context), user: User = Depends(require_permission(CLAIMS_RECONCILE))):
    staff = db.scalar(select(Staff).where(Staff.person_id == user.person_id, Staff.facility_id == facility_id, Staff.status == "ACTIVE").limit(1))
    if staff is None:
        raise HTTPException(status_code=403, detail="FACILITY_ACCESS_DENIED")
    try:
        reconciliation = reconcile_claim(db, claim_id, facility_id, staff.id, payload.received_amount, actor_user_id=user.id)
        return ReconcileResponse(claim_id=reconciliation.claim_id, expected_amount=reconciliation.expected_amount, received_amount=reconciliation.received_amount, difference=reconciliation.difference, status=reconciliation.status)
    except ClaimsError as exc:
        raise _error(exc) from exc
