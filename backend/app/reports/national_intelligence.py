from datetime import date, datetime, timezone

from app.reports.national_intelligence_schemas import (
    NationalFacilitySignal,
    NationalIntelligenceAlert,
    NationalIntelligenceResponse,
)
from app.reports.national_service import build_national_report


def _severity(score: int) -> str:
    if score >= 70:
        return "CRITICAL"
    if score >= 45:
        return "HIGH"
    if score >= 20:
        return "MEDIUM"
    return "LOW"


def _alert(
    code: str,
    severity: str,
    category: str,
    title: str,
    summary: str,
    value: int | float,
    unit: str,
    recommendation: str,
) -> NationalIntelligenceAlert:
    return NationalIntelligenceAlert(
        code=code,
        severity=severity,  # type: ignore[arg-type]
        category=category,  # type: ignore[arg-type]
        title=title,
        summary=summary,
        value=value,
        unit=unit,
        recommendation=recommendation,
    )


def build_national_intelligence(
    db,
    start_date: date,
    end_date: date,
    *,
    actor_user_id,
) -> NationalIntelligenceResponse:
    report = build_national_report(db, start_date, end_date, actor_user_id=actor_user_id)
    ops = report.operations
    alerts: list[NationalIntelligenceAlert] = []

    if ops.integration_failed:
        alerts.append(_alert(
            "INTEGRATION_FAILURES",
            "CRITICAL",
            "INTEGRATIONS",
            "Integration delivery failures",
            "Outbound national transactions have failed and require operational review.",
            ops.integration_failed,
            "transactions",
            "Review failed transactions, provider responses and retry eligibility before resubmission.",
        ))
    if ops.integration_retrying:
        alerts.append(_alert(
            "INTEGRATION_RETRIES",
            "HIGH",
            "INTEGRATIONS",
            "Integration retry queue is active",
            "Outbound transactions are waiting for another delivery attempt.",
            ops.integration_retrying,
            "transactions",
            "Review provider health and retrying transaction history; avoid manual duplication while retries are active.",
        ))
    if ops.low_stock_items:
        alerts.append(_alert(
            "LOW_STOCK",
            "HIGH",
            "SUPPLY",
            "Facilities have low-stock inventory",
            "Inventory items are at or below their configured facility minimum quantity.",
            ops.low_stock_items,
            "items",
            "Review affected facilities and prioritise replenishment or redistribution of critical commodities.",
        ))
    if ops.rejected_claims:
        alerts.append(_alert(
            "REJECTED_CLAIMS",
            "HIGH",
            "FINANCING",
            "Rejected claims require rework",
            "Claims currently carry a rejected or denied status across active facilities.",
            ops.rejected_claims,
            "claims",
            "Open the claims workbench, classify rejection reasons and resubmit only after corrective action.",
        ))
    if ops.open_encounters:
        alerts.append(_alert(
            "OPEN_ENCOUNTERS",
            "MEDIUM",
            "CLINICAL_OPERATIONS",
            "Clinical encounters remain open",
            "Open encounters may represent active care or documentation that still requires completion.",
            ops.open_encounters,
            "encounters",
            "Review ageing and facility distribution; close completed encounters without interrupting active care.",
        ))
    if ops.open_invoices:
        alerts.append(_alert(
            "OPEN_INVOICES",
            "MEDIUM",
            "FINANCING",
            "Invoices remain open",
            "Open or partially settled invoices require financial follow-up.",
            ops.open_invoices,
            "invoices",
            "Review ageing, payer responsibility and patient balances before collection or reconciliation actions.",
        ))
    if ops.pending_prescriptions:
        alerts.append(_alert(
            "PENDING_PRESCRIPTIONS",
            "MEDIUM",
            "CLINICAL_OPERATIONS",
            "Prescriptions are awaiting pharmacy workflow",
            "Prescriptions remain in active workflow states and may need dispensing or completion.",
            ops.pending_prescriptions,
            "prescriptions",
            "Review pharmacy queues and prioritise clinically time-sensitive prescriptions.",
        ))

    facility_signals: list[NationalFacilitySignal] = []
    for facility in report.facilities:
        score = 0
        signals: list[str] = []
        if facility.claims_receivable > 0:
            score += 15
            signals.append("claims receivable is outstanding")
        if facility.encounters > 0 and facility.confirmed_payments == 0:
            score += 10
            signals.append("encounters recorded with no confirmed payments in period")
        if facility.claims > 0 and facility.claims_approved < facility.claims_amount:
            score += 15
            signals.append("claim value is not fully approved")
        if facility.billed > 0 and facility.confirmed_payments == 0:
            score += 20
            signals.append("billing recorded with no confirmed payments in period")
        if score:
            facility_signals.append(NationalFacilitySignal(
                facility_id=facility.facility_id,
                facility_code=facility.facility_code,
                facility_name=facility.facility_name,
                county=facility.county,
                score=min(score, 100),
                severity=_severity(score),  # type: ignore[arg-type]
                signals=signals,
            ))

    facility_signals.sort(key=lambda item: (-item.score, item.facility_name))
    severity_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
    alerts.sort(key=lambda item: (severity_order[item.severity], -float(item.value), item.title))

    return NationalIntelligenceResponse(
        start_date=start_date.isoformat(),
        end_date=end_date.isoformat(),
        generated_at=datetime.now(timezone.utc).isoformat(),
        alerts=alerts,
        facility_signals=facility_signals,
    )
