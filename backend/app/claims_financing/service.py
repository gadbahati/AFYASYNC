"""Claims financing intelligence — quality scoring, pipeline, denials."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.audit.service import record_audit
from app.billing.models import Invoice, InvoiceItem
from app.claims.models import Claim, ClaimItem, ClaimResponse, Reconciliation
from app.coverage.models import Coverage
from app.encounters.models import Encounter
from app.preauthorizations import models as preauth_models


def score_claim_quality(
    db: Session,
    *,
    claim_id: UUID,
    facility_id: UUID,
    actor_user_id: UUID | None = None,
) -> dict:
    """Heuristic claim quality / fraud-risk score (0–100, higher = cleaner)."""
    claim = db.get(Claim, claim_id)
    if claim is None:
        raise ValueError("CLAIM_NOT_FOUND")
    invoice = db.get(Invoice, claim.invoice_id)
    if invoice is None or invoice.facility_id != facility_id:
        raise ValueError("FACILITY_ACCESS_DENIED")

    score = 100
    flags: list[str] = []

    # Coverage quality
    coverage = db.get(Coverage, invoice.coverage_id) if invoice.coverage_id else None
    if coverage is None:
        score -= 25
        flags.append("MISSING_COVERAGE")
    elif coverage.verification_status != "VERIFIED":
        score -= 20
        flags.append("COVERAGE_NOT_VERIFIED")

    # Amount sanity
    amount = Decimal(str(claim.claim_amount or 0))
    if amount <= 0:
        score -= 30
        flags.append("ZERO_CLAIM_AMOUNT")
    elif amount > Decimal("500000"):
        score -= 10
        flags.append("HIGH_VALUE_CLAIM")

    items = list(db.scalars(select(ClaimItem).where(ClaimItem.claim_id == claim.id)))
    if not items:
        score -= 25
        flags.append("NO_CLAIM_ITEMS")
    else:
        item_sum = sum((Decimal(str(i.amount)) for i in items), Decimal("0"))
        if item_sum != amount.quantize(Decimal("0.01")) and abs(item_sum - amount) > Decimal("0.05"):
            score -= 15
            flags.append("ITEM_TOTAL_MISMATCH")

    # Duplicate service codes (possible upcoding pattern signal)
    codes = [i.service_code for i in items]
    if len(codes) != len(set(codes)) and len(codes) > 3:
        score -= 5
        flags.append("DUPLICATE_SERVICE_CODES")

    # Encounter linkage
    enc = db.get(Encounter, claim.encounter_id)
    if enc is None:
        score -= 20
        flags.append("MISSING_ENCOUNTER")
    elif getattr(enc, "coverage_mode", None) == "CASH":
        score -= 40
        flags.append("CASH_ENCOUNTER")

    # Preauth: high value without preauth record (soft signal)
    if amount > Decimal("50000"):
        try:
            PreAuth = preauth_models.PreAuthorization
            pre = db.scalar(
                select(PreAuth.id).where(
                    PreAuth.patient_id == claim.patient_id,
                    PreAuth.facility_id == facility_id,
                    PreAuth.status.in_(["APPROVED", "ACTIVE", "AUTHORIZED"]),
                ).limit(1)
            )
            if pre is None:
                score -= 8
                flags.append("HIGH_VALUE_NO_PREAUTH_FOUND")
        except Exception:
            pass

    score = max(0, min(100, score))
    band = "GREEN" if score >= 80 else "AMBER" if score >= 55 else "RED"

    record_audit(
        db,
        action="CLAIM_QUALITY_SCORE",
        resource_type="CLAIM",
        resource_id=str(claim.id),
        result=band,
        user_id=actor_user_id,
        facility_id=facility_id,
        patient_id=claim.patient_id,
        metadata={"score": score, "flags": flags},
        commit=False,
    )

    return {
        "claim_id": str(claim.id),
        "claim_number": claim.claim_id,
        "score": score,
        "band": band,
        "flags": flags,
        "claim_amount": str(amount),
        "status": claim.status,
        "notes": [
            "Heuristic quality score — not a clinical fraud determination",
            "RED claims should be reviewed before SHA submission",
        ],
    }


def financing_pipeline(db: Session, facility_id: UUID, *, days: int = 30) -> dict:
    """Facility claims pipeline snapshot for revenue operations."""
    days = min(max(days, 1), 180)
    since = datetime.now(timezone.utc) - timedelta(days=days)

    # Claims linked via invoice facility
    rows = db.execute(
        select(Claim.status, func.count(Claim.id), func.coalesce(func.sum(Claim.claim_amount), 0))
        .join(Invoice, Invoice.id == Claim.invoice_id)
        .where(
            Invoice.facility_id == facility_id,
            Claim.updated_at >= since,
        )
        .group_by(Claim.status)
    ).all()

    by_status = {}
    total_count = 0
    total_amount = Decimal("0")
    for status, cnt, amt in rows:
        by_status[status] = {"count": int(cnt), "amount": str(Decimal(str(amt)).quantize(Decimal("0.01")))}
        total_count += int(cnt)
        total_amount += Decimal(str(amt))

    rejected = int(by_status.get("REJECTED", {}).get("count", 0))
    submitted_like = sum(
        int(by_status.get(s, {}).get("count", 0))
        for s in ("SUBMITTED", "ACCEPTED", "UNDER_REVIEW", "PAID", "PARTIALLY_PAID", "REJECTED")
    )
    denial_rate = round(100.0 * rejected / submitted_like, 1) if submitted_like else None

    # Unreconciled accepted claims
    unreconciled = db.scalar(
        select(func.count(Claim.id))
        .join(Invoice, Invoice.id == Claim.invoice_id)
        .outerjoin(Reconciliation, Reconciliation.claim_id == Claim.id)
        .where(
            Invoice.facility_id == facility_id,
            Claim.status.in_(["ACCEPTED", "PARTIALLY_PAID", "PAID"]),
            Reconciliation.id.is_(None),
        )
    ) or 0

    return {
        "facility_id": str(facility_id),
        "window_days": days,
        "total_claims": total_count,
        "total_claim_amount": str(total_amount.quantize(Decimal("0.01"))),
        "by_status": by_status,
        "denial_rate_pct": denial_rate,
        "unreconciled_settleable": int(unreconciled),
        "notes": [
            "Use preflight before create_claim to cut preventable denials",
            "Quality-score RED claims before submission",
        ],
    }


def denial_analytics(db: Session, facility_id: UUID, *, limit: int = 50) -> dict:
    """Recent rejection reasons from payer responses."""
    limit = min(max(limit, 1), 200)
    q = (
        select(ClaimResponse, Claim)
        .join(Claim, Claim.id == ClaimResponse.claim_id)
        .join(Invoice, Invoice.id == Claim.invoice_id)
        .where(
            Invoice.facility_id == facility_id,
            ClaimResponse.status.in_(["REJECTED", "PARTIALLY_PAID"]),
        )
        .order_by(ClaimResponse.received_at.desc())
        .limit(limit)
    )
    rows = db.execute(q).all()
    items = []
    code_counts: dict[str, int] = {}
    for resp, claim in rows:
        code = resp.response_code or "UNKNOWN"
        code_counts[code] = code_counts.get(code, 0) + 1
        items.append(
            {
                "claim_id": str(claim.id),
                "claim_number": claim.claim_id,
                "status": resp.status,
                "response_code": resp.response_code,
                "response_message": resp.response_message,
                "received_at": resp.received_at.isoformat() if resp.received_at else None,
            }
        )
    top_codes = sorted(code_counts.items(), key=lambda x: -x[1])[:10]
    return {
        "facility_id": str(facility_id),
        "sample_size": len(items),
        "top_rejection_codes": [{"code": c, "count": n} for c, n in top_codes],
        "recent": items,
    }
