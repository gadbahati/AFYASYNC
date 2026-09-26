from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.claims.models import Claim
from app.coverage.models import Payer, PayerPlan
from app.billing.models import Invoice


def financing_overview(db: Session) -> dict:
    """National, payer-agnostic financing exchange posture.

    This does not replace or bypass any payer. It provides a common financing
    control plane so SHA, private insurers, employer schemes and other payers
    can use the same eligibility, benefit, claims and settlement primitives.
    """
    payers = list(db.scalars(select(Payer).order_by(Payer.name.asc())))
    active_payers = [p for p in payers if p.status == "ACTIVE"]
    active_plans = db.scalar(select(func.count(PayerPlan.id)).where(PayerPlan.status == "ACTIVE")) or 0
    claims_count = db.scalar(select(func.count(Claim.id))) or 0
    claims_amount = db.scalar(select(func.coalesce(func.sum(Claim.claim_amount), 0))) or 0
    paid_amount = db.scalar(select(func.coalesce(func.sum(Claim.paid_amount), 0))) or 0
    pending = db.scalar(select(func.count(Claim.id)).where(Claim.status.in_(["DRAFT", "SUBMITTED", "UNDER_REVIEW"]))) or 0

    return {
        "model": "PAYER_AGNOSTIC_FINANCING_EXCHANGE",
        "active_payers": len(active_payers),
        "active_plans": int(active_plans),
        "registered_payers": len(payers),
        "claims": {
            "count": int(claims_count),
            "submitted_value_kes": str(Decimal(str(claims_amount)).quantize(Decimal("0.01"))),
            "paid_value_kes": str(Decimal(str(paid_amount)).quantize(Decimal("0.01"))),
            "pending_count": int(pending),
        },
        "capabilities": {
            "multi_payer_registry": True,
            "benefit_rules": True,
            "real_time_coverage_decision": True,
            "preauthorisation": True,
            "claim_preflight": True,
            "claim_adjudication": True,
            "reconciliation": True,
            "sha_connector": True,
            "private_payer_ready": True,
            "offline_facility_operation": True,
        },
        "payers": [
            {
                "id": str(p.id),
                "name": p.name,
                "code": p.code,
                "type": p.payer_type,
                "status": p.status,
                "integration_status": p.integration_status,
            }
            for p in active_payers
        ],
        "position": "SHA is treated as one financing participant rather than the platform boundary.",
    }
