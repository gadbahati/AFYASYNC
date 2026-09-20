"""Multi-payer truth + out-of-pocket estimate (hardened)."""

from __future__ import annotations

from datetime import date
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.audit.service import record_audit
from app.coverage.models import Coverage, Payer, PayerBenefitRule, PayerPlan
from app.coverage.oop_schemas import (
    OopEstimateRequest,
    OopEstimateResponse,
    OopLineBreakdown,
    OopLineIn,
    PayerOption,
    StackedEstimate,
)
from app.patients.models import PatientFacility


def _line_total(line: OopLineIn) -> float:
    return round(float(line.quantity) * float(line.unit_price), 2)


def _coverage_eligibility(coverage: Coverage, today: date) -> str:
    if coverage.status != "ACTIVE":
        return "INACTIVE"
    if coverage.verification_status != "VERIFIED":
        return "UNVERIFIED"
    if coverage.start_date and today < coverage.start_date:
        return "NOT_YET_ACTIVE"
    if coverage.end_date and today > coverage.end_date:
        return "EXPIRED"
    return "ELIGIBLE"


def _find_rule(
    db: Session,
    *,
    coverage: Coverage,
    service_code: str | None,
    service_type: str | None,
    today: date,
) -> PayerBenefitRule | None:
    conditions = []
    if service_code:
        conditions.append(PayerBenefitRule.service_code == service_code.strip())
    if service_type:
        conditions.append(PayerBenefitRule.service_type == service_type.strip())
    if not conditions:
        return None
    rules = list(
        db.scalars(
            select(PayerBenefitRule)
            .where(
                PayerBenefitRule.payer_id == coverage.payer_id,
                or_(
                    PayerBenefitRule.payer_plan_id == coverage.payer_plan_id,
                    PayerBenefitRule.payer_plan_id.is_(None),
                ),
                PayerBenefitRule.status == "ACTIVE",
                or_(PayerBenefitRule.effective_from.is_(None), PayerBenefitRule.effective_from <= today),
                or_(PayerBenefitRule.effective_to.is_(None), PayerBenefitRule.effective_to >= today),
                or_(*conditions),
            )
            .order_by(
                PayerBenefitRule.payer_plan_id.desc(),
                PayerBenefitRule.service_code.desc(),
                PayerBenefitRule.service_type.desc(),
                PayerBenefitRule.created_at.desc(),
            )
            .limit(1)
        )
    )
    return rules[0] if rules else None


def _apply_rule(
    rule: PayerBenefitRule | None, requested: float
) -> tuple[float, float, str, str, float, float, float | None]:
    """Return covered, patient, decision, reason, payer_percent, copay, max."""
    if rule is None:
        return 0.0, requested, "NOT_COVERED", "BENEFIT_RULE_NOT_FOUND", 0.0, 0.0, None
    payer_percent = float(rule.payer_percent)
    copay = float(rule.fixed_patient_copay)
    maximum = float(rule.max_covered_amount) if rule.max_covered_amount is not None else None
    covered = requested * payer_percent / 100.0
    if maximum is not None:
        covered = min(covered, maximum)
    covered = max(0.0, min(covered, requested))
    patient = max(0.0, requested - covered) + copay
    # Cap patient share sensibly: never charge more than requested + copay already applied once
    patient = round(min(patient, requested + copay), 2)
    covered = round(covered, 2)
    decision = "COVERED" if covered > 0 else "NOT_COVERED"
    return covered, patient, decision, "BENEFIT_RULE_APPLIED", payer_percent, copay, maximum


def _score_coverage(
    db: Session,
    *,
    coverage: Coverage,
    payer: Payer,
    lines: list[OopLineIn],
    today: date,
) -> PayerOption:
    eligibility = _coverage_eligibility(coverage, today)
    notes: list[str] = []
    if eligibility != "ELIGIBLE":
        notes.append(f"Coverage not claimable: {eligibility}")

    if coverage.payer_plan_id is not None:
        plan = db.scalar(
            select(PayerPlan).where(
                PayerPlan.id == coverage.payer_plan_id,
                PayerPlan.payer_id == coverage.payer_id,
                PayerPlan.status == "ACTIVE",
            )
        )
        if plan is None:
            eligibility = "INACTIVE"
            notes.append("Linked payer plan is not active")

    breakdowns: list[OopLineBreakdown] = []
    gross = 0.0
    covered_total = 0.0
    patient_total = 0.0

    for line in lines:
        total = _line_total(line)
        gross += total
        if eligibility != "ELIGIBLE":
            breakdowns.append(
                OopLineBreakdown(
                    service_code=(line.service_code or None),
                    service_type=(line.service_type or None),
                    description=line.description,
                    line_total=total,
                    covered_amount=0.0,
                    patient_amount=total,
                    decision="NOT_COVERED",
                    reason_code=eligibility,
                )
            )
            patient_total += total
            continue

        rule = _find_rule(
            db,
            coverage=coverage,
            service_code=line.service_code,
            service_type=line.service_type,
            today=today,
        )
        covered, patient, decision, reason, _, _, _ = _apply_rule(rule, total)
        covered_total += covered
        patient_total += patient
        breakdowns.append(
            OopLineBreakdown(
                service_code=(line.service_code.strip() if line.service_code else None),
                service_type=(line.service_type.strip() if line.service_type else None),
                description=line.description,
                line_total=total,
                covered_amount=covered,
                patient_amount=patient,
                decision=decision,
                reason_code=reason,
            )
        )

    claimable = eligibility == "ELIGIBLE" and covered_total > 0
    confidence = "HIGH" if claimable else ("MEDIUM" if eligibility == "UNVERIFIED" else "LOW")
    if eligibility == "ELIGIBLE" and any(b.reason_code == "BENEFIT_RULE_NOT_FOUND" for b in breakdowns):
        confidence = "MEDIUM"
        notes.append("Some lines lack matching benefit rules — patient share may be high")

    return PayerOption(
        coverage_id=coverage.id,
        payer_id=coverage.payer_id,
        payer_code=payer.code,
        payer_name=payer.name,
        payer_plan_id=coverage.payer_plan_id,
        membership_number=coverage.membership_number,
        verification_status=coverage.verification_status,
        eligibility=eligibility,
        gross_total=round(gross, 2),
        covered_total=round(covered_total, 2),
        patient_oop=round(patient_total, 2),
        claimable=claimable,
        confidence=confidence,
        lines=breakdowns,
        notes=notes,
    )


def _stack_primary_secondary(options: list[PayerOption], gross: float) -> StackedEstimate | None:
    eligible = [o for o in options if o.eligibility == "ELIGIBLE" and o.claimable]
    if len(eligible) < 2:
        return None
    # Prefer SHA as primary when present; else lowest OOP
    sha = next((o for o in eligible if o.payer_code.upper() == "SHA"), None)
    primary = sha or min(eligible, key=lambda o: o.patient_oop)
    residual = max(0.0, gross - primary.covered_total)
    secondaries = [o for o in eligible if o.coverage_id != primary.coverage_id]
    if not secondaries or residual <= 0:
        return StackedEstimate(
            primary_coverage_id=primary.coverage_id,
            secondary_coverage_id=None,
            primary_payer_code=primary.payer_code,
            secondary_payer_code=None,
            gross_total=gross,
            primary_covered=primary.covered_total,
            secondary_covered=0.0,
            patient_oop=round(residual, 2),
            note="Single eligible payer after ranking",
        )
    secondary = min(secondaries, key=lambda o: o.patient_oop)
    # Simple residual COB: secondary covers up to its covered_total ratio of residual
    # Conservative: secondary covers min(residual, secondary.covered_total)
    sec_cover = min(residual, secondary.covered_total)
    patient = max(0.0, residual - sec_cover)
    return StackedEstimate(
        primary_coverage_id=primary.coverage_id,
        secondary_coverage_id=secondary.coverage_id,
        primary_payer_code=primary.payer_code,
        secondary_payer_code=secondary.payer_code,
        gross_total=gross,
        primary_covered=round(primary.covered_total, 2),
        secondary_covered=round(sec_cover, 2),
        patient_oop=round(patient, 2),
        note="Primary/secondary residual model — confirm with payer COB contracts before billing",
    )


def estimate_out_of_pocket(
    db: Session,
    *,
    payload: OopEstimateRequest,
    facility_id: UUID | None,
    actor_user_id: UUID,
    require_facility_enrollment: bool = True,
) -> OopEstimateResponse:
    today = date.today()
    warnings: list[str] = []

    if require_facility_enrollment:
        if facility_id is None:
            raise ValueError("FACILITY_REQUIRED")
        enrolled = db.scalar(
            select(PatientFacility.id).where(
                PatientFacility.patient_id == payload.person_id,
                PatientFacility.facility_id == facility_id,
                PatientFacility.status == "ACTIVE",
            )
        )
        if enrolled is None:
            raise ValueError("PATIENT_NOT_IN_FACILITY")

    gross = round(sum(_line_total(line) for line in payload.lines), 2)
    if gross <= 0:
        raise ValueError("INVALID_GROSS")

    coverages = list(
        db.scalars(
            select(Coverage)
            .where(Coverage.person_id == payload.person_id, Coverage.status == "ACTIVE")
            .order_by(Coverage.created_at.desc())
        )
    )

    options: list[PayerOption] = []
    for cov in coverages:
        payer = db.get(Payer, cov.payer_id)
        if payer is None or payer.status != "ACTIVE":
            continue
        options.append(
            _score_coverage(db, coverage=cov, payer=payer, lines=payload.lines, today=today)
        )

    # Sort: claimable first, then lower OOP, SHA preferred on ties
    def _rank(o: PayerOption) -> tuple:
        sha_boost = 0 if o.payer_code.upper() == "SHA" else 1
        return (0 if o.claimable else 1, o.patient_oop, sha_boost, o.payer_code)

    options.sort(key=_rank)

    preferred = None
    if payload.preferred_coverage_id:
        preferred = next((o for o in options if o.coverage_id == payload.preferred_coverage_id), None)
        if preferred is None:
            warnings.append("Preferred coverage not found among active covers")
        elif not preferred.claimable:
            warnings.append("Preferred coverage is not currently claimable")

    claimable_opts = [o for o in options if o.claimable]
    if preferred and preferred.claimable:
        recommended = preferred
    elif claimable_opts:
        recommended = claimable_opts[0]
    else:
        recommended = None
        warnings.append("No verified claimable coverage — cash path applies")

    stacked = _stack_primary_secondary(options, gross)

    recommended_oop = recommended.patient_oop if recommended else gross
    if stacked and stacked.patient_oop < recommended_oop:
        recommended_oop = stacked.patient_oop
        warnings.append("Stacked primary/secondary may reduce patient OOP further — verify COB rules")

    guidance = (
        "Present cash total and best verified payer estimate to the patient before care. "
        "SHA and private payers only apply when coverage is VERIFIED and benefit rules match."
    )

    result = OopEstimateResponse(
        person_id=payload.person_id,
        facility_id=facility_id,
        effective_date=today,
        gross_total=gross,
        cash_oop=gross,
        options=options,
        recommended_coverage_id=recommended.coverage_id if recommended else None,
        recommended_payer_code=recommended.payer_code if recommended else "CASH",
        recommended_patient_oop=round(recommended_oop, 2),
        stacked=stacked,
        warnings=warnings,
        guidance=guidance,
    )

    record_audit(
        db,
        action="OOP_ESTIMATE",
        resource_type="COVERAGE",
        resource_id=str(payload.person_id),
        result="SUCCESS",
        user_id=actor_user_id,
        facility_id=facility_id,
        patient_id=payload.person_id,
        metadata={
            "gross_total": gross,
            "options": len(options),
            "recommended_payer": result.recommended_payer_code,
            "recommended_oop": result.recommended_patient_oop,
        },
        commit=False,
    )
    return result
