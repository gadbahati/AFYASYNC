"""Lightweight claim fraud / integrity checks. Phase 118 — BAHATI GAD WANGWE."""
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.claims.models import Claim, ClaimItem


def scan_claim_fraud(db: Session, *, claim_id: UUID, facility_id: UUID) -> dict:
    claim = db.get(Claim, claim_id)
    if claim is None:
        return {"ok": False, "error": "CLAIM_NOT_FOUND", "flags": [], "score": 0, "band": "NONE"}

    from app.billing.models import Invoice

    invoice = db.get(Invoice, claim.invoice_id)
    if invoice is None or invoice.facility_id != facility_id:
        return {"ok": False, "error": "FACILITY_ACCESS_DENIED", "flags": [], "score": 0, "band": "NONE"}

    flags: list[dict] = []
    score = 0

    # Duplicate: same patient + payer + amount within 48h (other claims)
    window_start = datetime.now(timezone.utc) - timedelta(hours=48)
    dup_q = select(func.count()).select_from(Claim).where(
        Claim.patient_id == claim.patient_id,
        Claim.payer_id == claim.payer_id,
        Claim.id != claim.id,
        Claim.claim_amount == claim.claim_amount,
        Claim.updated_at >= window_start,
    )
    dup_count = db.scalar(dup_q) or 0
    if dup_count > 0:
        flags.append(
            {
                "code": "POSSIBLE_DUPLICATE_CLAIM",
                "severity": "high",
                "points": 40,
                "message": f"{dup_count} other claim(s) same patient/payer/amount in 48h",
            }
        )
        score += 40

    # Frequency: many claims same patient in 7 days
    week_start = datetime.now(timezone.utc) - timedelta(days=7)
    freq = (
        db.scalar(
            select(func.count())
            .select_from(Claim)
            .where(
                Claim.patient_id == claim.patient_id,
                Claim.id != claim.id,
                Claim.updated_at >= week_start,
            )
        )
        or 0
    )
    if freq >= 5:
        flags.append(
            {
                "code": "HIGH_CLAIM_FREQUENCY",
                "severity": "medium",
                "points": 25,
                "message": f"{freq} other claims for this patient in 7 days",
            }
        )
        score += 25

    # High amount threshold (KES)
    amount = Decimal(str(claim.claim_amount or 0))
    if amount >= Decimal("100000"):
        flags.append(
            {
                "code": "HIGH_VALUE_CLAIM",
                "severity": "medium",
                "points": 20,
                "message": f"Claim amount {amount} exceeds high-value threshold (100,000)",
            }
        )
        score += 20

    # Empty lines
    items = list(db.scalars(select(ClaimItem).where(ClaimItem.claim_id == claim.id)).all())
    if not items:
        flags.append(
            {
                "code": "NO_CLAIM_LINES",
                "severity": "high",
                "points": 30,
                "message": "Claim has no line items",
            }
        )
        score += 30

    # Repeated service codes on same claim
    codes = [i.service_code for i in items]
    if len(codes) != len(set(codes)):
        flags.append(
            {
                "code": "DUPLICATE_SERVICE_LINES",
                "severity": "low",
                "points": 10,
                "message": "Same service_code appears more than once on claim",
            }
        )
        score += 10

    score = min(score, 100)
    if score >= 60:
        band = "HIGH"
    elif score >= 30:
        band = "MEDIUM"
    elif score > 0:
        band = "LOW"
    else:
        band = "CLEAR"

    return {
        "ok": True,
        "claim_id": str(claim.id),
        "claim_number": claim.claim_id,
        "score": score,
        "band": band,
        "flags": flags,
        "developer": "BAHATI GAD WANGWE",
    }


def appeal_claim(
    db: Session,
    *,
    claim_id: UUID,
    facility_id: UUID,
    actor_user_id: UUID | None,
    reason: str,
    evidence_ref: str | None = None,
) -> dict:
    claim = db.get(Claim, claim_id)
    if claim is None:
        raise ValueError("CLAIM_NOT_FOUND")
    from app.billing.models import Invoice

    invoice = db.get(Invoice, claim.invoice_id)
    if invoice is None or invoice.facility_id != facility_id:
        raise ValueError("FACILITY_ACCESS_DENIED")
    if claim.status != "REJECTED":
        raise ValueError("ONLY_REJECTED_CLAIMS_CAN_APPEAL")
    reason = (reason or "").strip()
    if len(reason) < 10:
        raise ValueError("APPEAL_REASON_TOO_SHORT")

    claim.status = "UNDER_REVIEW"
    from app.audit.service import record_audit

    record_audit(
        db,
        action="CLAIM_APPEAL",
        resource_type="CLAIM",
        resource_id=str(claim.id),
        result="UNDER_REVIEW",
        user_id=actor_user_id,
        facility_id=facility_id,
        patient_id=claim.patient_id,
        metadata={
            "reason": reason[:1000],
            "evidence_ref": (evidence_ref or "")[:200],
            "previous_status": "REJECTED",
        },
        commit=False,
    )
    db.commit()
    db.refresh(claim)
    return {
        "claim_id": str(claim.id),
        "claim_number": claim.claim_id,
        "status": claim.status,
        "message": "Appeal accepted — claim moved to UNDER_REVIEW",
        "developer": "BAHATI GAD WANGWE",
    }
