from datetime import date
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.audit.service import record_audit
from app.coverage.adjudication_schemas import BenefitAdjudicationRequest, BenefitAdjudicationResponse
from app.coverage.models import Coverage, PayerBenefitRule, PayerPlan


def adjudicate_benefit(
    db: Session,
    *,
    payload: BenefitAdjudicationRequest,
    facility_id: UUID,
    actor_user_id: UUID,
) -> BenefitAdjudicationResponse:
    today = date.today()
    coverage = db.scalar(select(Coverage).where(Coverage.id == payload.coverage_id).with_for_update())
    if coverage is None or coverage.status != "ACTIVE":
        raise ValueError("COVERAGE_NOT_ACTIVE")
    if coverage.verification_status != "VERIFIED":
        raise ValueError("COVERAGE_NOT_VERIFIED")
    if coverage.start_date and today < coverage.start_date:
        raise ValueError("COVERAGE_NOT_YET_ACTIVE")
    if coverage.end_date and today > coverage.end_date:
        raise ValueError("COVERAGE_EXPIRED")

    # Coverage itself is national payer data, but the person must be enrolled
    # in the requesting facility. This preserves facility isolation.
    from app.patients.models import PatientFacility
    enrolled = db.scalar(select(PatientFacility.id).where(
        PatientFacility.patient_id == coverage.person_id,
        PatientFacility.facility_id == facility_id,
        PatientFacility.status == "ACTIVE",
    ))
    if enrolled is None:
        raise ValueError("PATIENT_NOT_IN_FACILITY")

    plan = None
    if coverage.payer_plan_id is not None:
        plan = db.scalar(select(PayerPlan).where(
            PayerPlan.id == coverage.payer_plan_id,
            PayerPlan.payer_id == coverage.payer_id,
            PayerPlan.status == "ACTIVE",
        ))
        if plan is None:
            raise ValueError("COVERAGE_PLAN_NOT_ACTIVE")

    if not payload.service_code and not payload.service_type:
        raise ValueError("BENEFIT_SCOPE_REQUIRED")

    conditions = []
    if payload.service_code:
        conditions.append(PayerBenefitRule.service_code == payload.service_code.strip())
    if payload.service_type:
        conditions.append(PayerBenefitRule.service_type == payload.service_type.strip())

    rules = list(db.scalars(select(PayerBenefitRule).where(
        PayerBenefitRule.payer_id == coverage.payer_id,
        or_(PayerBenefitRule.payer_plan_id == coverage.payer_plan_id, PayerBenefitRule.payer_plan_id.is_(None)),
        PayerBenefitRule.status == "ACTIVE",
        or_(PayerBenefitRule.effective_from.is_(None), PayerBenefitRule.effective_from <= today),
        or_(PayerBenefitRule.effective_to.is_(None), PayerBenefitRule.effective_to >= today),
        or_(*conditions),
    ).order_by(
        PayerBenefitRule.payer_plan_id.desc(),
        PayerBenefitRule.service_code.desc(),
        PayerBenefitRule.service_type.desc(),
        PayerBenefitRule.created_at.desc(),
    ).limit(1)))
    rule = rules[0] if rules else None
    if rule is None:
        decision = "NOT_COVERED"
        reason = "BENEFIT_RULE_NOT_FOUND"
        covered = 0.0
        patient = float(payload.requested_amount)
        payer_percent = 0.0
        copay = 0.0
        maximum = None
    else:
        payer_percent = float(rule.payer_percent)
        copay = float(rule.fixed_patient_copay)
        maximum = float(rule.max_covered_amount) if rule.max_covered_amount is not None else None
        covered = float(payload.requested_amount) * payer_percent / 100.0
        if maximum is not None:
            covered = min(covered, maximum)
        covered = max(0.0, min(covered, float(payload.requested_amount)))
        patient = max(0.0, float(payload.requested_amount) - covered) + copay
        patient = min(patient, float(payload.requested_amount) + copay)
        decision = "COVERED" if covered > 0 else "NOT_COVERED"
        reason = "BENEFIT_RULE_APPLIED"

    result = BenefitAdjudicationResponse(
        coverage_id=coverage.id,
        person_id=coverage.person_id,
        payer_id=coverage.payer_id,
        payer_plan_id=coverage.payer_plan_id,
        service_code=payload.service_code.strip() if payload.service_code else None,
        service_type=payload.service_type.strip() if payload.service_type else None,
        requested_amount=float(payload.requested_amount),
        covered_amount=round(covered, 2),
        patient_amount=round(patient, 2),
        payer_percent=round(payer_percent, 2),
        fixed_patient_copay=round(copay, 2),
        max_covered_amount=maximum,
        decision=decision,
        reason_code=reason,
        effective_date=today,
    )
    record_audit(
        db,
        action="BENEFIT_ADJUDICATION",
        resource_type="COVERAGE",
        resource_id=str(coverage.id),
        result=decision,
        user_id=actor_user_id,
        facility_id=facility_id,
        patient_id=coverage.person_id,
        metadata={
            "payer_id": str(coverage.payer_id),
            "payer_plan_id": str(coverage.payer_plan_id) if coverage.payer_plan_id else None,
            "service_code": result.service_code,
            "service_type": result.service_type,
            "requested_amount": result.requested_amount,
            "covered_amount": result.covered_amount,
            "reason_code": reason,
        },
        commit=False,
    )
    db.commit()
    return result
