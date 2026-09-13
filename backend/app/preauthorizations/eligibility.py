from datetime import date
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.coverage.models import Coverage, Payer, PayerBenefitRule, PayerPlan


class EligibilityError(ValueError):
    pass


def check_coverage_eligibility(
    db: Session,
    *,
    patient_id: UUID,
    coverage_id: UUID,
    service_code: str | None = None,
    service_type: str | None = None,
    as_of: date | None = None,
) -> dict:
    """Return a deterministic eligibility decision from persisted coverage data.

    This is intentionally payer-neutral: external payer/SHA verification can be
    layered on later without making core care depend on an external service.
    """
    if not service_code and not service_type:
        raise EligibilityError("ELIGIBILITY_SERVICE_REQUIRED")

    coverage = db.scalar(
        select(Coverage).where(
            Coverage.id == coverage_id,
            Coverage.person_id == patient_id,
        )
    )
    if coverage is None:
        raise EligibilityError("COVERAGE_NOT_FOUND")
    if coverage.status != "ACTIVE":
        return {"eligible": False, "reason": "COVERAGE_NOT_ACTIVE", "coverage_id": coverage.id}

    today = as_of or date.today()
    if coverage.start_date and coverage.start_date > today:
        return {"eligible": False, "reason": "COVERAGE_NOT_STARTED", "coverage_id": coverage.id}
    if coverage.end_date and coverage.end_date < today:
        return {"eligible": False, "reason": "COVERAGE_EXPIRED", "coverage_id": coverage.id}
    if coverage.verification_status != "VERIFIED":
        return {"eligible": False, "reason": "VERIFICATION_REQUIRED", "coverage_id": coverage.id}

    payer = db.get(Payer, coverage.payer_id)
    if payer is None or payer.status != "ACTIVE":
        return {"eligible": False, "reason": "PAYER_NOT_ACTIVE", "coverage_id": coverage.id}

    if coverage.payer_plan_id:
        plan = db.get(PayerPlan, coverage.payer_plan_id)
        if plan is None or plan.status != "ACTIVE":
            return {"eligible": False, "reason": "PLAN_NOT_ACTIVE", "coverage_id": coverage.id}

    rules = list(
        db.scalars(
            select(PayerBenefitRule).where(
                PayerBenefitRule.payer_id == coverage.payer_id,
                PayerBenefitRule.status == "ACTIVE",
                (PayerBenefitRule.effective_from.is_(None) | (PayerBenefitRule.effective_from <= today)),
                (PayerBenefitRule.effective_to.is_(None) | (PayerBenefitRule.effective_to >= today)),
            )
        ).all()
    )

    def rank(rule: PayerBenefitRule) -> int:
        if coverage.payer_plan_id and rule.payer_plan_id == coverage.payer_plan_id and rule.service_code == service_code:
            return 4
        if coverage.payer_plan_id and rule.payer_plan_id == coverage.payer_plan_id and rule.service_type == service_type and rule.service_code is None:
            return 3
        if rule.payer_plan_id is None and rule.service_code == service_code:
            return 2
        if rule.payer_plan_id is None and rule.service_type == service_type and rule.service_code is None:
            return 1
        return 0

    matches = sorted((rule for rule in rules if rank(rule) > 0), key=lambda rule: (rank(rule), rule.created_at), reverse=True)
    rule = matches[0] if matches else None
    if rule is None:
        return {"eligible": False, "reason": "BENEFIT_NOT_CONFIGURED", "coverage_id": coverage.id, "payer_id": coverage.payer_id, "payer_plan_id": coverage.payer_plan_id}

    return {
        "eligible": True,
        "reason": "ELIGIBLE",
        "coverage_id": coverage.id,
        "payer_id": coverage.payer_id,
        "payer_plan_id": coverage.payer_plan_id,
        "benefit_rule_id": rule.id,
        "payer_percent": rule.payer_percent,
        "fixed_patient_copay": rule.fixed_patient_copay,
        "max_covered_amount": rule.max_covered_amount,
    }
