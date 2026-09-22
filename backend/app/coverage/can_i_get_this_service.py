"""Can I Get This? — eligibility, coverage, limits, auth, patient responsibility."""

from __future__ import annotations

from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.audit.service import record_audit
from app.coverage.can_i_get_this_schemas import (
    CanIGetThisRequest,
    CanIGetThisResponse,
    DocumentRequirement,
    PayerDecision,
)
from app.coverage.models import Coverage, Payer, PayerBenefitRule
from app.patients.models import Person

# Optional utilisation table may not exist until migration — import safely
try:
    from app.coverage.utilisation_models import BenefitUtilisation
except Exception:  # pragma: no cover
    BenefitUtilisation = None  # type: ignore


def _money(value: float | Decimal) -> Decimal:
    return Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _eligibility(coverage: Coverage, today: date) -> str:
    if coverage.status != "ACTIVE":
        return "INACTIVE"
    if getattr(coverage, "verification_status", "VERIFIED") not in {"VERIFIED", "ACTIVE", None}:
        # tolerate missing verification as UNVERIFIED only when explicitly set
        vs = getattr(coverage, "verification_status", None)
        if vs and vs not in {"VERIFIED"}:
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
    service_code: str,
    service_type: str | None,
    today: date,
) -> PayerBenefitRule | None:
    conditions = [PayerBenefitRule.service_code == service_code.strip()]
    if service_type:
        conditions = [
            or_(
                PayerBenefitRule.service_code == service_code.strip(),
                PayerBenefitRule.service_type == service_type.strip(),
            )
        ]
    rows = list(
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
                *conditions if service_type is None else [
                    or_(
                        PayerBenefitRule.service_code == service_code.strip(),
                        PayerBenefitRule.service_type == service_type.strip(),
                    )
                ],
            )
            .order_by(
                # Prefer exact service_code match via python sort below
                PayerBenefitRule.created_at.desc(),
            )
            .limit(20)
        )
    )
    if not rows:
        return None
    # Prefer exact service_code, then plan-specific, then type
    def rank(r: PayerBenefitRule) -> tuple:
        exact = 0 if (r.service_code or "").strip() == service_code.strip() else 1
        plan = 0 if r.payer_plan_id is not None else 1
        return (exact, plan)

    rows.sort(key=rank)
    return rows[0]


def _utilised_ytd(db: Session, coverage_id: UUID, service_code: str, year: int) -> Decimal:
    if BenefitUtilisation is None:
        return Decimal("0.00")
    total = db.scalar(
        select(func.coalesce(func.sum(BenefitUtilisation.amount), 0)).where(
            BenefitUtilisation.coverage_id == coverage_id,
            BenefitUtilisation.service_code == service_code,
            BenefitUtilisation.calendar_year == year,
            BenefitUtilisation.status == "POSTED",
        )
    )
    return _money(total or 0)


def _rule_excluded(rule: PayerBenefitRule | None) -> bool:
    if rule is None:
        return False
    return bool(getattr(rule, "is_excluded", False))


def _rule_requires_auth(rule: PayerBenefitRule | None) -> bool:
    if rule is None:
        return False
    return bool(getattr(rule, "requires_preauth", False))


def _rule_annual_limit(rule: PayerBenefitRule | None) -> Decimal | None:
    if rule is None:
        return None
    val = getattr(rule, "annual_limit_amount", None)
    if val is None:
        # fall back to max_covered_amount as soft annual if set
        val = getattr(rule, "max_covered_amount", None)
    return _money(val) if val is not None else None


def _rule_documents(rule: PayerBenefitRule | None) -> list[DocumentRequirement]:
    if rule is None:
        return []
    raw = getattr(rule, "required_documents", None)
    if not raw:
        docs: list[DocumentRequirement] = []
        if _rule_requires_auth(rule):
            docs.append(
                DocumentRequirement(
                    code="PREAUTH_FORM",
                    description="Valid preauthorisation / predetermination reference",
                )
            )
        return docs
    if isinstance(raw, list):
        out = []
        for item in raw:
            if isinstance(item, dict) and item.get("code"):
                out.append(
                    DocumentRequirement(
                        code=str(item["code"])[:40],
                        description=str(item.get("description") or item["code"])[:200],
                    )
                )
            elif isinstance(item, str):
                out.append(DocumentRequirement(code=item[:40], description=item[:200]))
        return out
    return []


def _apply_rule(
    rule: PayerBenefitRule | None,
    line_total: Decimal,
    remaining: Decimal | None,
) -> tuple[Decimal, Decimal, list[str]]:
    """Return (payer_amount, patient_amount, messages)."""
    msgs: list[str] = []
    if rule is None:
        msgs.append("No active benefit rule for this service under this payer — patient pays full amount on this coverage.")
        return Decimal("0.00"), line_total, msgs

    if _rule_excluded(rule):
        msgs.append("Service is excluded under this benefit rule.")
        return Decimal("0.00"), line_total, msgs

    percent = Decimal(str(getattr(rule, "payer_percent", 100) or 0))
    copay = _money(getattr(rule, "fixed_patient_copay", 0) or 0)
    max_cov = getattr(rule, "max_covered_amount", None)
    max_cov_d = _money(max_cov) if max_cov is not None else None

    gross_payer = _money(line_total * percent / Decimal("100"))
    if max_cov_d is not None:
        gross_payer = min(gross_payer, max_cov_d)
    if remaining is not None:
        if remaining <= 0:
            msgs.append("Annual / remaining benefit exhausted for this service.")
            return Decimal("0.00"), line_total, msgs
        if gross_payer > remaining:
            msgs.append("Payer amount capped by remaining benefit balance.")
            gross_payer = remaining

    patient = line_total - gross_payer
    if copay > 0:
        # Copay is additional patient responsibility, not exceeding line
        patient = min(line_total, patient + copay)
        gross_payer = max(Decimal("0.00"), line_total - patient)
        msgs.append(f"Fixed patient copay applied: {copay}")

    return _money(gross_payer), _money(patient), msgs


def can_i_get_this(
    db: Session,
    payload: CanIGetThisRequest,
    *,
    facility_id: UUID | None,
    actor_user_id: UUID | None,
) -> CanIGetThisResponse:
    person = db.get(Person, payload.person_id)
    if person is None:
        raise ValueError("PERSON_NOT_FOUND")
    if person.status == "DECEASED":
        raise ValueError("PERSON_DECEASED")

    today = payload.as_of or date.today()
    qty = Decimal(str(payload.quantity))
    price = Decimal(str(payload.unit_price))
    line_total = _money(qty * price)

    coverages = list(
        db.scalars(
            select(Coverage)
            .where(Coverage.person_id == payload.person_id)
            .order_by(Coverage.created_at.asc())
        )
    )

    decisions: list[PayerDecision] = []
    year = today.year

    for idx, cov in enumerate(coverages):
        payer = db.get(Payer, cov.payer_id)
        elig = _eligibility(cov, today)
        rule = _find_rule(
            db,
            coverage=cov,
            service_code=payload.service_code,
            service_type=payload.service_type,
            today=today,
        )
        utilised = _utilised_ytd(db, cov.id, payload.service_code.strip(), year)
        annual = _rule_annual_limit(rule)
        remaining = None
        if annual is not None:
            remaining = _money(max(Decimal("0.00"), annual - utilised))

        msgs: list[str] = []
        covered = False
        req_auth = False
        payer_amt = Decimal("0.00")
        patient_amt = line_total

        if elig != "ELIGIBLE":
            msgs.append(f"Coverage not eligible: {elig}")
        elif _rule_excluded(rule):
            elig = "EXCLUDED"
            msgs.append("Service excluded by benefit rule")
            payer_amt, patient_amt, extra = _apply_rule(rule, line_total, remaining)
            msgs.extend(extra)
        else:
            payer_amt, patient_amt, extra = _apply_rule(rule, line_total, remaining)
            msgs.extend(extra)
            covered = payer_amt > 0 or (rule is not None and not _rule_excluded(rule) and float(getattr(rule, "payer_percent", 0) or 0) > 0)
            req_auth = _rule_requires_auth(rule)
            if req_auth:
                msgs.append("Preauthorisation required before service")

        decisions.append(
            PayerDecision(
                coverage_id=cov.id,
                payer_id=cov.payer_id,
                payer_code=(payer.code if payer else "UNKNOWN"),
                payer_name=(payer.name if payer else "Unknown payer"),
                membership_number=getattr(cov, "membership_number", None),
                eligibility=elig,
                covered=covered and elig == "ELIGIBLE",
                requires_authorisation=req_auth,
                remaining_benefit=remaining,
                annual_limit=annual,
                utilised_ytd=utilised,
                expected_payer_amount=payer_amt if elig == "ELIGIBLE" else Decimal("0.00"),
                expected_patient_amount=patient_amt if elig == "ELIGIBLE" else line_total,
                rule_id=rule.id if rule else None,
                rule_version_note=(
                    f"effective {rule.effective_from} to {rule.effective_to}"
                    if rule and (rule.effective_from or rule.effective_to)
                    else ("active rule" if rule else None)
                ),
                coordination_rank=idx + 1,
                messages=msgs,
            )
        )

    # Coordination of benefits: primary = first eligible covered; secondary absorbs remainder
    primary_payer = Decimal("0.00")
    secondary_payer = Decimal("0.00")
    remaining_bill = line_total
    overall_eligible = False
    overall_covered = False
    requires_auth = False
    docs: list[DocumentRequirement] = []
    facility_reqs: list[str] = []

    ranked = sorted(
        [d for d in decisions if d.eligibility == "ELIGIBLE"],
        key=lambda d: d.coordination_rank,
    )
    for i, d in enumerate(ranked):
        overall_eligible = True
        if d.requires_authorisation:
            requires_auth = True
        if not d.covered:
            continue
        overall_covered = True
        take = min(d.expected_payer_amount, remaining_bill)
        if i == 0:
            primary_payer = take
        else:
            secondary_payer = _money(secondary_payer + take)
        remaining_bill = _money(remaining_bill - take)
        if remaining_bill <= 0:
            break

    # Collect documents from primary eligible rule
    for d in ranked:
        if d.rule_id:
            rule = db.get(PayerBenefitRule, d.rule_id)
            docs.extend(_rule_documents(rule))
            break

    if requires_auth:
        facility_reqs.append("Obtain / confirm preauthorisation before performing service")
    if line_total > 0 and primary_payer + secondary_payer < line_total:
        facility_reqs.append("Collect patient share or confirm cash path before service")

    patient_resp = remaining_bill
    cash_fallback = line_total

    guidance: list[str] = []
    if not coverages:
        guidance.append("No coverage on file — cash / self-pay path.")
        summary = "No active coverage. Patient pays full amount."
    elif not overall_eligible:
        guidance.append("No eligible coverage for the as-of date — check expiry and verification.")
        summary = "Not eligible under recorded coverages on this date."
    elif not overall_covered:
        guidance.append("Eligible membership(s) found but service not covered or excluded.")
        summary = "Eligible but not covered for this service."
    else:
        summary = (
            f"Covered estimate: payer {primary_payer + secondary_payer}, "
            f"patient {patient_resp}"
            + ("; preauthorisation required" if requires_auth else "")
        )
        if requires_auth:
            guidance.append("Do not render until authorisation is confirmed.")
        if patient_resp > 0:
            guidance.append(f"Inform patient of estimated out-of-pocket: {patient_resp} KES (or facility currency).")

    record_audit(
        db,
        action="CAN_I_GET_THIS",
        resource_type="PERSON",
        resource_id=str(payload.person_id),
        result="SUCCESS",
        user_id=actor_user_id,
        facility_id=facility_id,
        patient_id=payload.person_id,
        metadata={
            "service_code": payload.service_code,
            "line_total": str(line_total),
            "patient_responsibility": str(patient_resp),
            "as_of": today.isoformat(),
        },
        commit=False,
    )

    return CanIGetThisResponse(
        service_code=payload.service_code.strip(),
        service_type=payload.service_type,
        service_name=payload.service_name,
        as_of=today,
        line_total=line_total,
        overall_eligible=overall_eligible,
        overall_covered=overall_covered,
        requires_authorisation=requires_auth,
        primary_payer_amount=primary_payer,
        secondary_payer_amount=secondary_payer,
        patient_responsibility=patient_resp,
        cash_fallback_amount=cash_fallback,
        documents_required=docs,
        facility_requirements=facility_reqs,
        payers=decisions,
        summary=summary,
        guidance=guidance,
    )


def post_utilisation(
    db: Session,
    *,
    coverage_id: UUID,
    person_id: UUID,
    service_code: str,
    amount: Decimal,
    actor_user_id: UUID | None,
    facility_id: UUID | None,
    reference: str | None = None,
) -> None:
    """Post utilisation against a coverage (e.g. after claim approval)."""
    if BenefitUtilisation is None:
        raise ValueError("UTILISATION_NOT_AVAILABLE")
    today = date.today()
    row = BenefitUtilisation(
        coverage_id=coverage_id,
        person_id=person_id,
        service_code=service_code.strip(),
        amount=_money(amount),
        calendar_year=today.year,
        status="POSTED",
        reference=reference,
        facility_id=facility_id,
    )
    db.add(row)
    db.flush()
    record_audit(
        db,
        action="BENEFIT_UTILISATION_POSTED",
        resource_type="COVERAGE",
        resource_id=str(coverage_id),
        result="SUCCESS",
        user_id=actor_user_id,
        facility_id=facility_id,
        patient_id=person_id,
        metadata={"service_code": service_code, "amount": str(_money(amount))},
        commit=False,
    )
