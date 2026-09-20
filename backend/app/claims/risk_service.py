"""Phase 11 — SHA / payer rejection prevention risk engine.

Scores invoices and open claims for rejection likelihood using real
structural checks (not dummy data). Hard errors → high risk + block.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.claims.models import Claim, ClaimResponse
from app.claims.preflight_service import preflight_claim
from app.claims.service import ClaimsError

# Hard errors that typically cause immediate rejection / invalid claim
HARD_ERROR_WEIGHT = 25
SOFT_WARNING_WEIGHT = 8
MAX_SCORE = 100

# Map known preflight codes → points (hard)
ERROR_POINTS: dict[str, int] = {
    "INVOICE_VOID": 40,
    "PAYER_COVERAGE_REQUIRED": 35,
    "CASH_ENCOUNTER_NO_CLAIM": 40,
    "VERIFIED_COVERAGE_REQUIRED": 30,
    "COVERAGE_EXPIRED": 35,
    "COVERAGE_NOT_YET_ACTIVE": 30,
    "CLAIM_ALREADY_EXISTS": 20,
    "CLAIM_ITEMS_REQUIRED": 35,
    "CLAIM_INVOICE_TOTAL_MISMATCH": 30,
    "INVOICE_TOTAL_INTEGRITY_ERROR": 35,
    "INVOICE_ITEM_RESPONSIBILITY_MISMATCH": 28,
    "NEGATIVE_INVOICE_ITEM_AMOUNT": 40,
    "ENCOUNTER_MISMATCH": 40,
    "CHARGE_SCOPE_MISMATCH": 35,
    "PATIENT_NOT_IN_FACILITY": 25,
    "PAYER_NOT_ACTIVE": 30,
    "PAYER_NOT_FOUND": 35,
    "COVERAGE_NOT_FOUND": 35,
    "COVERAGE_INVOICE_MISMATCH": 30,
    "ENCOUNTER_NOT_FOUND": 40,
    "SERVICE_NOT_FOUND": 25,
    "CHARGE_NOT_FOUND": 25,
}

WARNING_POINTS: dict[str, int] = {
    "PAYER_INTEGRATION_NOT_CONFIGURED": 15,
}


@dataclass
class RiskFactor:
    code: str
    severity: str  # HARD | SOFT
    points: int
    message: str
    owner: str = "BILLING"


@dataclass
class RiskResult:
    score: int
    band: str  # LOW | MEDIUM | HIGH | CRITICAL
    block_submit: bool
    factors: list[RiskFactor] = field(default_factory=list)
    payer_amount: float = 0.0
    ready: bool = False
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def _band(score: int) -> str:
    if score >= 70:
        return "CRITICAL"
    if score >= 45:
        return "HIGH"
    if score >= 20:
        return "MEDIUM"
    return "LOW"


def _owner_for(code: str) -> str:
    if "COVERAGE" in code or "PAYER" in code:
        return "RECEPTION / COVERAGE"
    if "ENCOUNTER" in code or "PATIENT" in code:
        return "CLINICAL"
    if "INTEGRATION" in code:
        return "IT / INTEGRATIONS"
    return "BILLING"


def score_from_preflight(
    *,
    errors: list[str],
    warnings: list[str],
    payer_amount: float,
) -> RiskResult:
    factors: list[RiskFactor] = []
    total = 0
    for code in errors:
        pts = ERROR_POINTS.get(code, HARD_ERROR_WEIGHT)
        total += pts
        factors.append(
            RiskFactor(
                code=code,
                severity="HARD",
                points=pts,
                message=f"Hard check failed: {code.replace('_', ' ').title()}",
                owner=_owner_for(code),
            )
        )
    for code in warnings:
        pts = WARNING_POINTS.get(code, SOFT_WARNING_WEIGHT)
        total += pts
        factors.append(
            RiskFactor(
                code=code,
                severity="SOFT",
                points=pts,
                message=f"Warning: {code.replace('_', ' ').title()}",
                owner=_owner_for(code),
            )
        )
    score = min(MAX_SCORE, total)
    block = len(errors) > 0 or score >= 70
    return RiskResult(
        score=score,
        band=_band(score),
        block_submit=block,
        factors=factors,
        payer_amount=payer_amount,
        ready=len(errors) == 0,
        errors=list(errors),
        warnings=list(warnings),
    )


def score_invoice(
    db: Session,
    *,
    invoice_id: UUID,
    facility_id: UUID,
    actor_user_id: UUID,
) -> RiskResult:
    """Run preflight then attach risk score (single source of truth)."""
    pre = preflight_claim(
        db,
        invoice_id=invoice_id,
        facility_id=facility_id,
        actor_user_id=actor_user_id,
    )
    return score_from_preflight(
        errors=pre.errors,
        warnings=pre.warnings,
        payer_amount=pre.payer_amount,
    )


def facility_kes_at_risk(
    db: Session,
    *,
    facility_id: UUID,
    days: int = 7,
) -> dict:
    """Aggregate claim value that is rejected or still open and aging.

    Uses real claims scoped by invoice→facility via encounter join is expensive;
    claims are facility-scoped in list endpoints via service — here we filter
    claims whose invoice belongs to this facility.
    """
    from app.billing.models import Invoice

    days = max(1, min(days, 90))
    since = datetime.now(timezone.utc) - timedelta(days=days)

    # Claims for invoices at this facility
    rows = list(
        db.execute(
            select(Claim, Invoice)
            .join(Invoice, Invoice.id == Claim.invoice_id)
            .where(
                Invoice.facility_id == facility_id,
                Claim.updated_at >= since,
            )
        ).all()
    )

    rejected_kes = Decimal("0")
    in_flight_kes = Decimal("0")
    draft_kes = Decimal("0")
    rejected_count = 0
    in_flight_count = 0
    draft_count = 0

    for claim, _inv in rows:
        amt = Decimal(str(claim.claim_amount or 0))
        if claim.status == "REJECTED":
            rejected_kes += amt
            rejected_count += 1
        elif claim.status in {"SUBMITTED", "UNDER_REVIEW"}:
            in_flight_kes += amt
            in_flight_count += 1
        elif claim.status in {"DRAFT", "READY"}:
            draft_kes += amt
            draft_count += 1

    # At-risk = rejected (needs rework) + in-flight (uncertainty) weighted lighter for draft
    at_risk = rejected_kes + in_flight_kes

    return {
        "facility_id": str(facility_id),
        "window_days": days,
        "kes_at_risk": float(at_risk),
        "kes_rejected": float(rejected_kes),
        "kes_in_flight": float(in_flight_kes),
        "kes_draft_or_ready": float(draft_kes),
        "count_rejected": rejected_count,
        "count_in_flight": in_flight_count,
        "count_draft_or_ready": draft_count,
        "as_of": datetime.now(timezone.utc).isoformat(),
    }
