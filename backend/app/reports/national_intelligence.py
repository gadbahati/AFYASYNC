from datetime import date, datetime, timedelta, timezone

from app.reports.national_intelligence_schemas import (
    NationalCountyIntelligence,
    NationalFacilitySignal,
    NationalIntelligenceAlert,
    NationalIntelligenceResponse,
    NationalIntelligenceTrend,
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


def _alert(code: str, severity: str, category: str, title: str, summary: str, value: int | float, unit: str, recommendation: str) -> NationalIntelligenceAlert:
    return NationalIntelligenceAlert(code=code, severity=severity, category=category, title=title, summary=summary, value=value, unit=unit, recommendation=recommendation)


def _trend(metric: str, label: str, current: float, previous: float) -> NationalIntelligenceTrend:
    if previous == 0:
        change = None if current == 0 else 100.0
    else:
        change = round(((current - previous) / abs(previous)) * 100, 2)
    if change is None or abs(change) < 1:
        direction = "FLAT"
    elif change > 0:
        direction = "UP"
    else:
        direction = "DOWN"
    if direction == "FLAT":
        interpretation = f"{label} is broadly stable versus the comparison period."
    elif direction == "UP":
        interpretation = f"{label} increased by {abs(change):.2f}% versus the comparison period."
    else:
        interpretation = f"{label} decreased by {abs(change):.2f}% versus the comparison period."
    return NationalIntelligenceTrend(metric=metric, label=label, current=round(current, 2), previous=round(previous, 2), change_percent=change, direction=direction, interpretation=interpretation)


def build_national_intelligence(db, start_date: date, end_date: date, *, actor_user_id) -> NationalIntelligenceResponse:
    report = build_national_report(db, start_date, end_date, actor_user_id=actor_user_id)
    period_days = (end_date - start_date).days + 1
    comparison_end = start_date - timedelta(days=1)
    comparison_start = comparison_end - timedelta(days=period_days - 1)
    previous = build_national_report(db, comparison_start, comparison_end, actor_user_id=actor_user_id)
    ops = report.operations
    alerts: list[NationalIntelligenceAlert] = []

    if ops.integration_failed:
        alerts.append(_alert("INTEGRATION_FAILURES", "CRITICAL", "INTEGRATIONS", "Integration delivery failures", "Outbound national transactions have failed and require operational review.", ops.integration_failed, "transactions", "Review failed transactions, provider responses and retry eligibility before resubmission."))
    if ops.integration_retrying:
        alerts.append(_alert("INTEGRATION_RETRIES", "HIGH", "INTEGRATIONS", "Integration retry queue is active", "Outbound transactions are waiting for another delivery attempt.", ops.integration_retrying, "transactions", "Review provider health and retrying transaction history; avoid manual duplication while retries are active."))
    if ops.low_stock_items:
        alerts.append(_alert("LOW_STOCK", "HIGH", "SUPPLY", "Facilities have low-stock inventory", "Inventory items are at or below their configured facility minimum quantity.", ops.low_stock_items, "items", "Review affected facilities and prioritise replenishment or redistribution of critical commodities."))
    if ops.rejected_claims:
        alerts.append(_alert("REJECTED_CLAIMS", "HIGH", "FINANCING", "Rejected claims require rework", "Claims currently carry a rejected or denied status across active facilities.", ops.rejected_claims, "claims", "Open the claims workbench, classify rejection reasons and resubmit only after corrective action."))
    if ops.open_encounters:
        alerts.append(_alert("OPEN_ENCOUNTERS", "MEDIUM", "CLINICAL_OPERATIONS", "Clinical encounters remain open", "Open encounters may represent active care or documentation that still requires completion.", ops.open_encounters, "encounters", "Review ageing and facility distribution; close completed encounters without interrupting active care."))
    if ops.open_invoices:
        alerts.append(_alert("OPEN_INVOICES", "MEDIUM", "FINANCING", "Invoices remain open", "Open or partially settled invoices require financial follow-up.", ops.open_invoices, "invoices", "Review ageing, payer responsibility and patient balances before collection or reconciliation actions."))
    if ops.pending_prescriptions:
        alerts.append(_alert("PENDING_PRESCRIPTIONS", "MEDIUM", "CLINICAL_OPERATIONS", "Prescriptions are awaiting pharmacy workflow", "Prescriptions remain in active workflow states and may need dispensing or completion.", ops.pending_prescriptions, "prescriptions", "Review pharmacy queues and prioritise clinically time-sensitive prescriptions."))

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
            facility_signals.append(NationalFacilitySignal(facility_id=facility.facility_id, facility_code=facility.facility_code, facility_name=facility.facility_name, county=facility.county, score=min(score, 100), severity=_severity(score), signals=signals))
    facility_signals.sort(key=lambda item: (-item.score, item.facility_name))

    trends = [
        _trend("encounters", "Encounters", float(report.encounters), float(previous.encounters)),
        _trend("invoices_total", "Invoice value", float(report.invoices_total), float(previous.invoices_total)),
        _trend("confirmed_payments", "Confirmed payments", float(report.confirmed_payments), float(previous.confirmed_payments)),
        _trend("claims", "Claims", float(report.claims), float(previous.claims)),
        _trend("claims_receivable", "Claims receivable", float(report.claims_receivable), float(previous.claims_receivable)),
    ]

    county_map: dict[str, dict[str, object]] = {}
    for facility in report.facilities:
        county = (facility.county or "Unspecified").strip() or "Unspecified"
        entry = county_map.setdefault(county, {"facilities": 0, "review": 0, "encounters": 0, "billed": 0.0, "payments": 0.0, "receivable": 0.0, "scores": []})
        entry["facilities"] = int(entry["facilities"]) + 1
        entry["encounters"] = int(entry["encounters"]) + facility.encounters
        entry["billed"] = float(entry["billed"]) + float(facility.billed)
        entry["payments"] = float(entry["payments"]) + float(facility.confirmed_payments)
        entry["receivable"] = float(entry["receivable"]) + float(facility.claims_receivable)
    for signal in facility_signals:
        county = (signal.county or "Unspecified").strip() or "Unspecified"
        entry = county_map.setdefault(county, {"facilities": 0, "review": 0, "encounters": 0, "billed": 0.0, "payments": 0.0, "receivable": 0.0, "scores": []})
        entry["review"] = int(entry["review"]) + 1
        entry["scores"].append(signal.score)

    counties: list[NationalCountyIntelligence] = []
    for county, entry in county_map.items():
        scores = [int(x) for x in entry["scores"]]
        counties.append(NationalCountyIntelligence(
            county=county,
            facilities=int(entry["facilities"]),
            facilities_requiring_review=int(entry["review"]),
            encounters=int(entry["encounters"]),
            billed=round(float(entry["billed"]), 2),
            confirmed_payments=round(float(entry["payments"]), 2),
            claims_receivable=round(float(entry["receivable"]), 2),
            average_review_score=round(sum(scores) / len(scores), 2) if scores else 0.0,
            highest_review_score=max(scores) if scores else 0,
        ))
    counties.sort(key=lambda item: (-item.facilities_requiring_review, -item.claims_receivable, item.county))

    severity_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
    alerts.sort(key=lambda item: (severity_order[item.severity], -float(item.value), item.title))
    return NationalIntelligenceResponse(start_date=start_date.isoformat(), end_date=end_date.isoformat(), comparison_start_date=comparison_start.isoformat(), comparison_end_date=comparison_end.isoformat(), generated_at=datetime.now(timezone.utc).isoformat(), alerts=alerts, facility_signals=facility_signals, trends=trends, counties=counties)
