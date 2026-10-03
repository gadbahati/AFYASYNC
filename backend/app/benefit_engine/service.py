"""Universal Benefits & Tariff Engine — rule matching and quote calculation.

Phase 103 hardens matching so the most specific active rule wins:
  service_code + plan > service_code > service_type + plan > service_type

Developer: BAHATI GAD WANGWE
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.benefit_engine.models import BenefitRuleVersion


def _money(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _specificity(rule: BenefitRuleVersion, *, payer_plan_id: UUID | None, service_code: str | None) -> int:
    score = 0
    if rule.service_code and service_code and rule.service_code == service_code:
        score += 100
    elif rule.service_code:
        score += 0  # code rule that did not match should not appear in candidates
    if rule.service_type:
        score += 20
    if rule.payer_plan_id is not None and payer_plan_id is not None and rule.payer_plan_id == payer_plan_id:
        score += 40
    elif rule.payer_plan_id is None:
        score += 5  # plan-agnostic fallback
    score += min(int(rule.version or 1), 50)
    return score


def find_rule(
    db: Session,
    *,
    payer_id: UUID,
    payer_plan_id: UUID | None,
    package_id: UUID | None,
    service_code: str | None,
    service_type: str | None,
    as_of: date,
) -> BenefitRuleVersion | None:
    """Return the highest-specificity ACTIVE rule effective on as_of."""
    code = (service_code or "").strip() or None
    stype = (service_type or "").strip() or None

    conditions = [
        BenefitRuleVersion.payer_id == payer_id,
        BenefitRuleVersion.status == "ACTIVE",
        BenefitRuleVersion.effective_from <= as_of,
        or_(BenefitRuleVersion.effective_to.is_(None), BenefitRuleVersion.effective_to >= as_of),
    ]
    if package_id is not None:
        conditions.append(BenefitRuleVersion.benefit_package_id == package_id)
    if payer_plan_id is not None:
        conditions.append(
            or_(BenefitRuleVersion.payer_plan_id == payer_plan_id, BenefitRuleVersion.payer_plan_id.is_(None))
        )

    scope_filters = []
    if code:
        scope_filters.append(BenefitRuleVersion.service_code == code)
    if stype:
        scope_filters.append(BenefitRuleVersion.service_type == stype)
    if not scope_filters:
        return None
    conditions.append(or_(*scope_filters))

    candidates = list(db.scalars(select(BenefitRuleVersion).where(*conditions)).all())
    if not candidates:
        return None

    # Drop code-specific rules that do not match the requested code
    ranked: list[tuple[int, BenefitRuleVersion]] = []
    for rule in candidates:
        if rule.service_code and code and rule.service_code != code:
            continue
        if rule.service_code and not code:
            # requesting by type only should not pick pure code rules unless type matches
            if rule.service_type and stype and rule.service_type != stype:
                continue
            if not rule.service_type:
                continue
        if rule.service_type and stype and rule.service_type != stype and not (
            rule.service_code and code and rule.service_code == code
        ):
            # type mismatch unless exact code match
            continue
        ranked.append((_specificity(rule, payer_plan_id=payer_plan_id, service_code=code), rule))

    if not ranked:
        return None
    ranked.sort(key=lambda x: x[0], reverse=True)
    return ranked[0][1]


def _apply_rule(rule: BenefitRuleVersion, gross: Decimal) -> dict:
    explanation: list[str] = []
    if rule.is_excluded:
        return {
            "decision": "INELIGIBLE",
            "reason_code": "SERVICE_EXCLUDED",
            "allowed_amount": Decimal("0"),
            "payer_amount": Decimal("0"),
            "patient_amount": gross,
            "requires_preauth": False,
            "explanation": ["Service is excluded by the active benefit rule."],
        }

    if rule.tariff_amount is not None:
        tariff = Decimal(str(rule.tariff_amount))
        allowed = min(gross, tariff)
        explanation.append(f"Tariff ceiling {tariff} applied against gross {gross}.")
    else:
        allowed = gross
        explanation.append("No tariff ceiling; allowed amount equals gross.")

    payer_pct = Decimal(str(rule.payer_percent))
    copay = Decimal(str(rule.fixed_patient_copay or 0))
    payer = _money((allowed * payer_pct / Decimal("100")) - copay)
    payer = max(Decimal("0"), payer)
    payer = min(payer, allowed)
    explanation.append(f"Payer share {payer_pct}% of allowed minus copay {copay}.")

    if rule.max_covered_amount is not None:
        cap = Decimal(str(rule.max_covered_amount))
        if payer > cap:
            explanation.append(f"Max covered amount {cap} capped payer share.")
            payer = cap

    if rule.requires_preauth:
        decision = "CONDITIONAL"
        reason = "PREAUTH_REQUIRED"
        explanation.append("Preauthorization is required before full cover.")
    else:
        decision = "ELIGIBLE"
        reason = "ACTIVE_BENEFIT_RULE"

    patient = _money(max(Decimal("0"), gross - payer))
    return {
        "decision": decision,
        "reason_code": reason,
        "allowed_amount": _money(allowed),
        "payer_amount": _money(payer),
        "patient_amount": patient,
        "requires_preauth": bool(rule.requires_preauth),
        "explanation": explanation,
    }


def quote(db: Session, payload) -> dict:
    as_of = payload.as_of or date.today()
    gross = _money(Decimal(str(payload.gross_amount)))
    rule = find_rule(
        db,
        payer_id=payload.payer_id,
        payer_plan_id=payload.payer_plan_id,
        package_id=payload.benefit_package_id,
        service_code=payload.service_code,
        service_type=payload.service_type,
        as_of=as_of,
    )
    if rule is None:
        return {
            "matched": False,
            "rule_id": None,
            "package_id": None,
            "version": None,
            "tariff_amount": None,
            "gross_amount": float(gross),
            "allowed_amount": float(gross),
            "payer_amount": 0.0,
            "patient_amount": float(gross),
            "currency": "KES",
            "decision": "UNKNOWN",
            "reason_code": "NO_ACTIVE_BENEFIT_RULE",
            "requires_preauth": False,
            "explanation": [
                "No ACTIVE benefit rule matched payer/plan/service for the quote date.",
                "Patient remains responsible until a tariff/benefit rule is configured.",
            ],
            "as_of": as_of.isoformat(),
            "developer": "BAHATI GAD WANGWE",
        }

    applied = _apply_rule(rule, gross)
    return {
        "matched": True,
        "rule_id": rule.id,
        "package_id": rule.benefit_package_id,
        "version": rule.version,
        "rule_name": rule.name,
        "tariff_amount": float(rule.tariff_amount) if rule.tariff_amount is not None else None,
        "gross_amount": float(gross),
        "allowed_amount": float(applied["allowed_amount"]),
        "payer_amount": float(applied["payer_amount"]),
        "patient_amount": float(applied["patient_amount"]),
        "currency": rule.currency or "KES",
        "decision": applied["decision"],
        "reason_code": applied["reason_code"],
        "requires_preauth": applied["requires_preauth"],
        "explanation": applied["explanation"],
        "as_of": as_of.isoformat(),
        "developer": "BAHATI GAD WANGWE",
    }


def quote_lines(db: Session, *, payer_id: UUID, payer_plan_id: UUID | None, package_id: UUID | None, as_of: date | None, lines: list[dict]) -> dict:
    """Batch quote for claim/invoice lines. Each line: service_code?, service_type?, gross_amount, line_id?."""
    day = as_of or date.today()
    results = []
    payer_total = Decimal("0")
    patient_total = Decimal("0")
    unknown = 0
    preauth = 0
    ineligible = 0
    for line in lines:
        class _P:
            pass

        payload = _P()
        payload.payer_id = payer_id
        payload.payer_plan_id = payer_plan_id
        payload.benefit_package_id = package_id
        payload.service_code = line.get("service_code")
        payload.service_type = line.get("service_type")
        payload.gross_amount = line.get("gross_amount", 0)
        payload.as_of = day
        q = quote(db, payload)
        q["line_id"] = line.get("line_id")
        results.append(q)
        payer_total += Decimal(str(q["payer_amount"]))
        patient_total += Decimal(str(q["patient_amount"]))
        if not q["matched"]:
            unknown += 1
        if q.get("requires_preauth"):
            preauth += 1
        if q.get("decision") == "INELIGIBLE":
            ineligible += 1

    return {
        "as_of": day.isoformat(),
        "line_count": len(results),
        "unknown_rules": unknown,
        "preauth_required_lines": preauth,
        "ineligible_lines": ineligible,
        "payer_total": float(_money(payer_total)),
        "patient_total": float(_money(patient_total)),
        "lines": results,
        "developer": "BAHATI GAD WANGWE",
    }
