from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.adjudication.models import ClaimAdjudication, ClaimLineAdjudication
from app.adjudication.schemas import AdjudicationResponse, AdjudicationRunRequest
from app.adjudication.service import AdjudicationError, adjudicate
from app.auth.dependencies import get_facility_context, require_permission
from app.billing.models import Invoice
from app.claims.models import Claim
from app.database import get_db
from app.rbac.models import User

router = APIRouter(prefix="/api/v1/adjudication", tags=["Claims adjudication"])


@router.post("/run", response_model=AdjudicationResponse)
def run_adjudication(
    payload: AdjudicationRunRequest,
    db: Session = Depends(get_db),
    facility_id: UUID = Depends(get_facility_context),
    user: User = Depends(require_permission("claims.validate")),
):
    try:
        return adjudicate(
            db,
            claim_id=payload.claim_id,
            facility_id=facility_id,
            actor_user_id=user.id,
            force=payload.force,
        )
    except AdjudicationError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/claims/{claim_id}", response_model=AdjudicationResponse)
def get_adjudication(
    claim_id: UUID,
    db: Session = Depends(get_db),
    facility_id: UUID = Depends(get_facility_context),
    user: User = Depends(require_permission("claims.validate")),
):
    _ = user
    claim = db.get(Claim, claim_id)
    if claim is None:
        raise HTTPException(status_code=404, detail="CLAIM_NOT_FOUND")
    invoice = db.get(Invoice, claim.invoice_id)
    if invoice is None or invoice.facility_id != facility_id:
        raise HTTPException(status_code=403, detail="FACILITY_ACCESS_DENIED")
    row = db.scalar(select(ClaimAdjudication).where(ClaimAdjudication.claim_id == claim_id))
    if row is None:
        raise HTTPException(status_code=404, detail="ADJUDICATION_NOT_FOUND")
    return row


@router.get("/claims/{claim_id}/lines")
def get_adjudication_lines(
    claim_id: UUID,
    db: Session = Depends(get_db),
    facility_id: UUID = Depends(get_facility_context),
    user: User = Depends(require_permission("claims.validate")),
):
    """Line-level adjudication breakdown for the claims workbench."""
    _ = user
    claim = db.get(Claim, claim_id)
    if claim is None:
        raise HTTPException(status_code=404, detail="CLAIM_NOT_FOUND")
    invoice = db.get(Invoice, claim.invoice_id)
    if invoice is None or invoice.facility_id != facility_id:
        raise HTTPException(status_code=403, detail="FACILITY_ACCESS_DENIED")
    adj = db.scalar(select(ClaimAdjudication).where(ClaimAdjudication.claim_id == claim_id))
    if adj is None:
        return {"claim_id": str(claim_id), "decision": None, "lines": []}
    lines = list(
        db.scalars(
            select(ClaimLineAdjudication).where(ClaimLineAdjudication.adjudication_id == adj.id)
        ).all()
    )
    return {
        "claim_id": str(claim_id),
        "adjudication_id": str(adj.id),
        "decision": adj.decision,
        "submitted_amount": float(adj.submitted_amount),
        "allowed_amount": float(adj.allowed_amount),
        "patient_amount": float(adj.patient_amount),
        "reason_code": adj.reason_code,
        "adjudicated_at": adj.adjudicated_at.isoformat() if adj.adjudicated_at else None,
        "lines": [
            {
                "id": str(ln.id),
                "claim_item_id": str(ln.claim_item_id),
                "submitted_amount": float(ln.submitted_amount),
                "allowed_amount": float(ln.allowed_amount),
                "decision": ln.decision,
                "reason_code": ln.reason_code,
                "evidence": ln.evidence,
            }
            for ln in lines
        ],
    }
