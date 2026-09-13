from datetime import date
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit.service import record_audit
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
    actor_user_id: UUID | None = None,
    facility_id: UUID | None = None,
) -> dict:
    """Evaluate persisted coverage and benefit configuration without external payer dependency."""
    if not service_code and not service_type:
        raise EligibilityError("ELIGIBILITY_SERVICE_REQUIRED")

    coverage = db.scalar(select(Coverage).where(Coverage.id == coverage_id, Coverage.person_id == patient_id))
    if coverage is None:
        raise EligibilityError("COVERAGE_NOT_FOUND")

    today = as_of or date.today()
    reason = None
    payer = db.get(Payer, coverage.payer_id)
    plan = db.get(PayerPlan, coverage.payer_plan_id) if coverage.payer_plan_id else None

    if coverage.status != "ACTIVE":
        reason = "COVERAGE_NOT_ACTIVE"
    elif coverage.start_date and coverage.start_date > today:
        reason = "COVERAGE_NOT_STARTED"
    elif coverage.end_date and coverage.end_date < today:
        reason = "COVERAGE_EXPIRED"
    elif coverage.verification_status != "VERIFIED":
        reason = "VERIFICATION_REQUIRED"
    elif payer is None or payer.status != "ACTIVE":
        reason = "PAYER_NOT_ACTIVE"
    elif coverage.payer_plan_id and (plan is None or plan.status != "ACTIVE"):
        reason = "PLAN_NOT_ACTIVE"

    rule = None
    if reason is None:
        rules = list(db.scalars(select(PayerBenefitRule).where(
            PayerBenefitRule.payer_id == coverage.payer_id,
            PayerBenefitRule.status == "ACTIVE",
            (PayerBenefitRule.effective_from.is_(None) | (PayerBenefitRule.effective_from <= today)),
            (PayerBenefitRule.effective_to.is_(None) | (PayerBenefitRule.effective_to >= today)),
        )).all())

        def rank(candidate: PayerBenefitRule) -> int:
            if coverage.payer_plan_id and candidate.payer_plan_id == coverage.payer_plan_id and candidate.service_code == service_code:
                return 4
            if coverage.payer_plan_id and candidate.payer_plan_id == coverage.payer_plan_id and candidate.service_type == service_type and candidate.service_code is None:
                return 3
            if candidate.payer_plan_id is None and candidate.service_code == service_code:
                return 2
            if candidate.payer_plan_id is None and candidate.service_type == service_type and candidate.service_code is None:
                return 1
            return 0

        matches = sorted((candidate for candidate in rules if rank(candidate) > 0), key=lambda candidate: (rank(candidate), candidate.created_at), reverse=True)
        rule = matches[0] if matches else None
        if rule is None:
            reason = "BENEFIT_NOT_CONFIGURED"

    eligible = reason is None
    result = {
        "eligible": eligible,
        "reason": "ELIGIBLE" if eligible else reason,
        "coverage_id": coverage.id,
        "payer_id": coverage.payer_id,
        "payer_plan_id": coverage.payer_plan_id,
        "benefit_rule_id": rule.id if rule else None,
        "payer_percent": rule.payer_percent if rule else None,
        "fixed_patient_copay": rule.fixed_patient_copay if rule else None,
        "max_covered_amount": rule.max_covered_amount if rule else None,
    }
    record_audit(
        db,
        action="CHECK_COVERAGE_ELIGIBILITY",
        resource_type="COVERAGE",
        resource_id=str(coverage.id),
        result="ELIGIBLE" if eligible else "INELIGIBLE",
        user_id=actor_user_id,
        facility_id=facility_id,
        patient_id=patient_id,
        metadata={"service_code": service_code, "service_type": service_type, "reason": result["reason"], "benefit_rule_id": str(rule.id) if rule else None},
        commit=True,
    )
    return result
