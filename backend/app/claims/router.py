from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.dependencies import get_facility_context, require_permission
from app.context.service import resolve_facility_ids
from app.billing.models import Invoice
from app.claims.fraud_service import appeal_claim, scan_claim_fraud
from app.claims.models import Claim, ClaimResponse
from app.claims.permissions import CLAIMS_CREATE, CLAIMS_RECONCILE, CLAIMS_SUBMIT, CLAIMS_VALIDATE
from app.claims.rejection_guide import guide_for
from app.claims.schemas import (
    ClaimCreate,
    ClaimResponseOut,
    ClaimSubmitOut,
    ClaimValidationOut,
    PayerResponseCreate,
    ReconcileCreate,
    ReconcileResponse,
)
from app.claims.service import ClaimsError, create_claim, record_payer_response, reconcile_claim, submit_claim, validate_claim
from app.config import settings
from app.database import get_db
from app.rbac.models import Staff, User

router = APIRouter(prefix="/api/v1/claims", tags=["Claims"])

_STATUS_ALIASES = {
    "APPROVED": "ACCEPTED",
    "PARTIALLY_APPROVED": "PARTIALLY_PAID",
    "PROCESSING": "UNDER_REVIEW",
}


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


def _error(exc: ClaimsError) -> HTTPException:
    mapping = {
        "CLAIM_NOT_FOUND": 404,
        "INVOICE_NOT_FOUND": 404,
        "FACILITY_ACCESS_DENIED": 403,
        "CLAIM_NOT_VALID": 409,
        "CLAIM_NOT_SUBMITTABLE": 409,
        "CLAIM_ALREADY_EXISTS": 409,
    }
    return HTTPException(status_code=mapping.get(str(exc), 409), detail=str(exc))


@router.get("", response_model=list[ClaimResponseOut])
def list_claims(
    limit: int = Query(50, ge=1, le=200),
    scope: str = Query("facility"),
    db: Session = Depends(get_db),
    facility_id: UUID = Depends(get_facility_context),
    user: User = Depends(require_permission(CLAIMS_CREATE)),
):
    _ = user
    facility_ids = resolve_facility_ids(db, facility_id, scope)
    q = (
        select(Claim)
        .join(Invoice, Invoice.id == Claim.invoice_id)
        .where(Invoice.facility_id.in_(facility_ids))
        .order_by(Claim.updated_at.desc())
        .limit(limit)
    )
    return list(db.scalars(q).all())


@router.get("/workbench/rejections", response_model=list[RejectionWorkbenchItem])
def rejection_workbench(
    db: Session = Depends(get_db),
    facility_id: UUID = Depends(get_facility_context),
    user: User = Depends(require_permission(CLAIMS_VALIDATE)),
):
    _ = user
    claims = list(
        db.scalars(
            select(Claim)
            .join(Invoice, Invoice.id == Claim.invoice_id)
            .where(Invoice.facility_id == facility_id, Claim.status == "REJECTED")
            .order_by(Claim.updated_at.desc())
            .limit(100)
        ).all()
    )
    items: list[RejectionWorkbenchItem] = []
    for c in claims:
        resp = db.scalar(
            select(ClaimResponse).where(ClaimResponse.claim_id == c.id).order_by(ClaimResponse.id.desc()).limit(1)
        )
        code = resp.response_code if resp else None
        g = guide_for(code or "UNKNOWN")
        items.append(
            RejectionWorkbenchItem(
                claim_id=c.id,
                claim_number=c.claim_id,
                invoice_id=c.invoice_id,
                status=c.status,
                claim_amount=float(c.claim_amount),
                response_code=code,
                response_message=resp.response_message if resp else None,
                guide_code=g.get("code", "UNKNOWN"),
                guide_title=g.get("title", "Rejection"),
                guide_fix=g.get("action", ""),
                guide_owner=g.get("owner", "Claims"),
            )
        )
    return items


@router.get("/{claim_id}/rejection-guide")
def claim_rejection_guide(
    claim_id: UUID,
    db: Session = Depends(get_db),
    facility_id: UUID = Depends(get_facility_context),
    user: User = Depends(require_permission(CLAIMS_VALIDATE)),
):
    _ = user
    claim = db.get(Claim, claim_id)
    if claim is None:
        raise HTTPException(status_code=404, detail="CLAIM_NOT_FOUND")
    inv = db.get(Invoice, claim.invoice_id)
    if inv is None or inv.facility_id != facility_id:
        raise HTTPException(status_code=403, detail="FACILITY_ACCESS_DENIED")
    resp = db.scalar(
        select(ClaimResponse).where(ClaimResponse.claim_id == claim.id).order_by(ClaimResponse.id.desc()).limit(1)
    )
    code = resp.response_code if resp else "UNKNOWN"
    return guide_for(code or "UNKNOWN")


@router.post("/{claim_id}/sandbox-reject", response_model=ClaimResponseOut)
def sandbox_reject(
    claim_id: UUID,
    db: Session = Depends(get_db),
    facility_id: UUID = Depends(get_facility_context),
    user: User = Depends(require_permission(CLAIMS_VALIDATE)),
):
    if settings.is_production:
        raise HTTPException(status_code=403, detail="SANDBOX_ONLY")
    claim = db.get(Claim, claim_id)
    if claim is None:
        raise HTTPException(status_code=404, detail="CLAIM_NOT_FOUND")
    inv = db.get(Invoice, claim.invoice_id)
    if inv is None or inv.facility_id != facility_id:
        raise HTTPException(status_code=403, detail="FACILITY_ACCESS_DENIED")
    claim.status = "REJECTED"
    db.add(
        ClaimResponse(
            claim_id=claim.id,
            status="REJECTED",
            response_code="SANDBOX_REJECT",
            response_message="Sandbox rejection for testing",
            external_reference="SANDBOX",
        )
    )
    db.commit()
    db.refresh(claim)
    return claim


@router.post("", response_model=ClaimResponseOut, status_code=201)
def create(
    payload: ClaimCreate,
    db: Session = Depends(get_db),
    facility_id: UUID = Depends(get_facility_context),
    user: User = Depends(require_permission(CLAIMS_CREATE)),
):
    try:
        return create_claim(db, facility_id, payload.invoice_id, actor_user_id=user.id)
    except ClaimsError as exc:
        raise _error(exc) from exc


@router.post("/{claim_id}/validate", response_model=ClaimValidationOut)
def validate(
    claim_id: UUID,
    db: Session = Depends(get_db),
    facility_id: UUID = Depends(get_facility_context),
    user: User = Depends(require_permission(CLAIMS_VALIDATE)),
):
    try:
        return validate_claim(db, claim_id, facility_id, actor_user_id=user.id)
    except ClaimsError as exc:
        raise _error(exc) from exc


@router.post("/{claim_id}/submit", response_model=ClaimSubmitOut)
def submit(
    claim_id: UUID,
    db: Session = Depends(get_db),
    facility_id: UUID = Depends(get_facility_context),
    user: User = Depends(require_permission(CLAIMS_SUBMIT)),
):
    try:
        return submit_claim(db, claim_id, facility_id, actor_user_id=user.id)
    except ClaimsError as exc:
        raise _error(exc) from exc


@router.post("/{claim_id}/response", response_model=ClaimResponseOut)
def payer_response(
    claim_id: UUID,
    payload: PayerResponseCreate,
    db: Session = Depends(get_db),
    facility_id: UUID = Depends(get_facility_context),
    user: User = Depends(require_permission(CLAIMS_VALIDATE)),
):
    try:
        return record_payer_response(
            db,
            claim_id,
            facility_id,
            payload,
            actor_user_id=user.id,
        )
    except ClaimsError as exc:
        raise _error(exc) from exc


@router.post("/{claim_id}/reconcile", response_model=ReconcileResponse)
def reconcile(
    claim_id: UUID,
    payload: ReconcileCreate,
    db: Session = Depends(get_db),
    facility_id: UUID = Depends(get_facility_context),
    user: User = Depends(require_permission(CLAIMS_RECONCILE)),
):
    staff = db.scalar(
        select(Staff).where(
            Staff.user_id == user.id,
            Staff.facility_id == facility_id,
            Staff.status == "ACTIVE",
        ).limit(1)
    )
    if staff is None:
        raise HTTPException(status_code=403, detail="FACILITY_ACCESS_DENIED")
    try:
        reconciliation = reconcile_claim(
            db,
            claim_id,
            facility_id,
            staff.id,
            payload.received_amount,
            actor_user_id=user.id,
        )
        return ReconcileResponse(
            claim_id=reconciliation.claim_id,
            expected_amount=reconciliation.expected_amount,
            received_amount=reconciliation.received_amount,
            difference=reconciliation.difference,
            status=reconciliation.status,
        )
    except ClaimsError as exc:
        raise _error(exc) from exc


@router.post("/{claim_id}/fraud-scan")
def fraud_scan(
    claim_id: UUID,
    db: Session = Depends(get_db),
    facility_id: UUID = Depends(get_facility_context),
    user: User = Depends(require_permission(CLAIMS_VALIDATE)),
):
    """Run integrity / fraud heuristics on a claim. Phase 118."""
    _ = user
    return scan_claim_fraud(db, claim_id=claim_id, facility_id=facility_id)


@router.post("/{claim_id}/appeal")
def claim_appeal(
    claim_id: UUID,
    payload: dict,
    db: Session = Depends(get_db),
    facility_id: UUID = Depends(get_facility_context),
    user: User = Depends(require_permission(CLAIMS_VALIDATE)),
):
    """Appeal a REJECTED claim → UNDER_REVIEW. Phase 118."""
    reason = str((payload or {}).get("reason") or "")
    evidence_ref = (payload or {}).get("evidence_ref")
    try:
        return appeal_claim(
            db,
            claim_id=claim_id,
            facility_id=facility_id,
            actor_user_id=user.id,
            reason=reason,
            evidence_ref=str(evidence_ref) if evidence_ref else None,
        )
    except ValueError as exc:
        code = str(exc)
        status = 404 if code == "CLAIM_NOT_FOUND" else (403 if code == "FACILITY_ACCESS_DENIED" else 409)
        raise HTTPException(status_code=status, detail=code) from exc
