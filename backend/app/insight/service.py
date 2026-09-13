from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.billing.models import Charge, Invoice
from app.claims.models import Claim
from app.coverage.models import Coverage, Payer
from app.encounters.models import Encounter
from app.insight.schemas import (
    CommandCentreMetric,
    CommandCentreResponse,
    CoverageSimulateRequest,
    CoverageSimulateResponse,
    FraudRadarResponse,
    FraudSignal,
    SimulatedLineResult,
)
from app.pharmacy.models import InventoryItem, Prescription


def simulate_coverage(db: Session, facility_id: UUID, payload: CoverageSimulateRequest) -> CoverageSimulateResponse:
    mode = payload.coverage_mode.upper()
    warnings: list[str] = []
    eligibility = "UNKNOWN"
    eligibility_detail = ""

    if mode == "CASH":
        eligibility = "NOT_REQUIRED"
        eligibility_detail = "Self-pay. No payer claim will be generated."
    elif mode == "SHA":
        eligibility = "LOOKUP_REQUIRED"
        eligibility_detail = "SHA membership must be verified at reception. Live national eligibility depends on authorised SHA connector."
        if payload.membership_number:
            # Local coverage table may hold attached SHA cover
            cov = db.scalar(
                select(Coverage)
                .join(Payer, Payer.id == Coverage.payer_id)
                .where(
                    Coverage.membership_number == payload.membership_number.strip(),
                    Payer.code == "SHA",
                )
                .limit(1)
            )
            if cov is not None:
                status = getattr(cov, "verification_status", None) or getattr(cov, "status", "UNKNOWN")
                eligibility = str(status).upper()
                eligibility_detail = f"Local SHA coverage record found (status={eligibility})."
            else:
                eligibility = "NOT_FOUND_LOCALLY"
                eligibility_detail = "No local SHA coverage for that membership number. Verify via SHA connector or attach after lookup."
                warnings.append("SHA membership not found in local coverage table")
        else:
            warnings.append("Provide membership_number for stronger SHA eligibility simulation")
    elif mode == "AFYASYNC":
        eligibility = "MEMBERSHIP_PATH"
        eligibility_detail = "AfyaSync standalone membership. Claims go to AFYASYNC payer when coverage is verified."
        if payload.patient_id:
            cov = db.scalar(
                select(Coverage)
                .join(Payer, Payer.id == Coverage.payer_id)
                .where(
                    Coverage.patient_id == payload.patient_id,
                    Payer.code == "AFYASYNC",
                )
                .limit(1)
            )
            if cov is None:
                warnings.append("Patient has no AFYASYNC coverage attached yet")
                eligibility = "NO_LOCAL_COVER"
            else:
                eligibility = str(getattr(cov, "verification_status", None) or getattr(cov, "status", "ACTIVE")).upper()
    else:
        eligibility = "OTHER_PAYER"
        eligibility_detail = "Other payer — configure integration and verification rules."

    lines_out: list[SimulatedLineResult] = []
    gross = Decimal("0")
    payer_total = Decimal("0")
    patient_total = Decimal("0")

    for line in payload.lines:
        qty = Decimal(str(line.quantity))
        unit = Decimal(str(line.unit_price))
        total = (qty * unit).quantize(Decimal("0.01"))
        gross += total

        if mode == "CASH":
            payer_share = Decimal("0.00")
            patient_share = total
            note = "Patient pays in full"
        elif mode == "SHA":
            # Conservative default: assume SHA covers 100% of listed tariff until package rules applied
            payer_share = total
            patient_share = Decimal("0.00")
            note = "Assumed SHA-covered pending package/tariff rules"
            if eligibility in {"NOT_FOUND_LOCALLY", "LAPSED", "INACTIVE", "REJECTED"}:
                payer_share = Decimal("0.00")
                patient_share = total
                note = "SHA not verified — treat as patient-pay until eligibility confirms"
        elif mode == "AFYASYNC":
            payer_share = total
            patient_share = Decimal("0.00")
            note = "AfyaSync membership assumed for listed services"
            if eligibility == "NO_LOCAL_COVER":
                payer_share = Decimal("0.00")
                patient_share = total
                note = "No AFYASYNC cover — patient-pay until enrolled"
        else:
            payer_share = (total * Decimal("0.5")).quantize(Decimal("0.01"))
            patient_share = total - payer_share
            note = "Other payer default 50/50 split until rules configured"

        payer_total += payer_share
        patient_total += patient_share
        lines_out.append(
            SimulatedLineResult(
                code=line.code,
                description=line.description,
                quantity=float(qty),
                unit_price=unit,
                line_total=total,
                payer_share=payer_share,
                patient_share=patient_share,
                note=note,
            )
        )

    claimable = mode in {"SHA", "AFYASYNC", "OTHER"} and patient_total < gross and eligibility not in {
        "NOT_FOUND_LOCALLY",
        "NO_LOCAL_COVER",
        "LAPSED",
        "INACTIVE",
        "REJECTED",
    }
    if mode == "CASH":
        claimable = False
        warnings.append("CASH encounters never produce payer claims")

    guidance = {
        "CASH": "Proceed with care. Collect patient payment at cashier. No claim.",
        "SHA": "Verify SHA membership, then treat. Build claim from invoice after care.",
        "AFYASYNC": "Confirm AfyaSync membership on patient record, then treat and claim if verified.",
        "OTHER": "Confirm other-payer contract and verification before high-cost care.",
    }.get(mode, "Review coverage before high-cost orders.")

    return CoverageSimulateResponse(
        coverage_mode=mode,
        eligibility=eligibility,
        eligibility_detail=eligibility_detail,
        gross_total=gross.quantize(Decimal("0.01")),
        payer_total=payer_total.quantize(Decimal("0.01")),
        patient_total=patient_total.quantize(Decimal("0.01")),
        claimable=claimable,
        warnings=warnings,
        lines=lines_out,
        guidance=guidance,
    )


def build_command_centre(db: Session, facility_id: UUID) -> CommandCentreResponse:
    now = datetime.now(timezone.utc)
    day_ago = now - timedelta(days=1)

    open_encounters = db.scalar(
        select(func.count()).select_from(Encounter).where(
            Encounter.facility_id == facility_id, Encounter.status == "OPEN"
        )
    ) or 0
    encounters_24h = db.scalar(
        select(func.count()).select_from(Encounter).where(
            Encounter.facility_id == facility_id, Encounter.started_at >= day_ago
        )
    ) or 0
    invoices_open = db.scalar(
        select(func.count()).select_from(Invoice).where(
            Invoice.facility_id == facility_id, Invoice.status.in_(["OPEN", "PARTIAL", "ISSUED", "PENDING"])
        )
    ) or 0
    low_stock = db.scalar(
        select(func.count()).select_from(InventoryItem).where(
            InventoryItem.facility_id == facility_id,
            InventoryItem.current_quantity <= InventoryItem.minimum_quantity,
        )
    ) or 0
    pending_rx = db.scalar(
        select(func.count())
        .select_from(Prescription)
        .join(Encounter, Encounter.id == Prescription.encounter_id)
        .where(Encounter.facility_id == facility_id, Prescription.status.in_(["PENDING", "ACTIVE", "PRESCRIBED"]))
    ) or 0

    claim_rows = db.execute(
        select(Claim.status, func.count())
        .select_from(Claim)
        .join(Invoice, Invoice.id == Claim.invoice_id)
        .where(Invoice.facility_id == facility_id)
        .group_by(Claim.status)
    ).all()
    claim_pipeline = {str(status): int(count) for status, count in claim_rows}

    mix_rows = db.execute(
        select(Encounter.coverage_mode, func.count())
        .where(Encounter.facility_id == facility_id)
        .group_by(Encounter.coverage_mode)
    ).all()
    coverage_mix = {str(mode or "UNKNOWN"): int(count) for mode, count in mix_rows}

    metrics = [
        CommandCentreMetric(key="open_encounters", label="Open encounters", value=int(open_encounters), tone="warn" if open_encounters > 50 else "neutral"),
        CommandCentreMetric(key="encounters_24h", label="Encounters (24h)", value=int(encounters_24h), tone="good"),
        CommandCentreMetric(key="open_invoices", label="Open / partial invoices", value=int(invoices_open), tone="warn" if invoices_open else "good"),
        CommandCentreMetric(key="pending_prescriptions", label="Pending prescriptions", value=int(pending_rx), tone="warn" if pending_rx else "good"),
        CommandCentreMetric(key="low_stock_items", label="Low / out-of-stock items", value=int(low_stock), tone="bad" if low_stock else "good"),
        CommandCentreMetric(key="claims_total", label="Claims on file", value=sum(claim_pipeline.values()), tone="neutral"),
    ]

    alerts: list[str] = []
    if low_stock:
        alerts.append(f"{low_stock} inventory item(s) at or below minimum quantity")
    if claim_pipeline.get("REJECTED") or claim_pipeline.get("DENIED"):
        alerts.append("Rejected/denied claims need rejection workbench attention")
    if open_encounters > 30:
        alerts.append("High open-encounter load — review queue and discharge")
    if not alerts:
        alerts.append("No critical operational alerts")

    return CommandCentreResponse(
        facility_id=facility_id,
        generated_at=now.isoformat(),
        metrics=metrics,
        claim_pipeline=claim_pipeline,
        coverage_mix=coverage_mix,
        alerts=alerts,
    )


def scan_fraud_signals(db: Session, facility_id: UUID) -> FraudRadarResponse:
    now = datetime.now(timezone.utc)
    signals: list[FraudSignal] = []

    # High value open invoices
    high_invoices = db.scalars(
        select(Invoice)
        .where(Invoice.facility_id == facility_id, Invoice.total_amount >= 50000)
        .order_by(Invoice.total_amount.desc())
        .limit(10)
    ).all()
    for inv in high_invoices:
        if inv.status not in {"PAID", "SETTLED", "CLOSED"}:
            signals.append(
                FraudSignal(
                    code="HIGH_VALUE_OPEN_INVOICE",
                    severity="MEDIUM",
                    title="High-value invoice not settled",
                    detail=f"Invoice {inv.invoice_id} total {inv.total_amount} status={inv.status}",
                    resource_type="INVOICE",
                    resource_id=str(inv.id),
                )
            )

    # Duplicate claim attempts same invoice
    dup_claims = db.execute(
        select(Claim.invoice_id, func.count())
        .select_from(Claim)
        .join(Invoice, Invoice.id == Claim.invoice_id)
        .where(Invoice.facility_id == facility_id)
        .group_by(Claim.invoice_id)
        .having(func.count() > 1)
    ).all()
    for invoice_id, count in dup_claims:
        signals.append(
            FraudSignal(
                code="MULTIPLE_CLAIMS_SAME_INVOICE",
                severity="HIGH",
                title="Multiple claims for one invoice",
                detail=f"Invoice {invoice_id} has {count} claim records",
                resource_type="INVOICE",
                resource_id=str(invoice_id),
            )
        )

    # Charges without linked encounter activity in weird volume
    charge_count = db.scalar(
        select(func.count()).select_from(Charge).where(Charge.facility_id == facility_id)
    ) or 0
    if charge_count == 0 and (db.scalar(select(func.count()).select_from(Encounter).where(Encounter.facility_id == facility_id)) or 0) > 20:
        signals.append(
            FraudSignal(
                code="ACTIVITY_WITHOUT_CHARGES",
                severity="LOW",
                title="Encounters without billing activity",
                detail="Facility has many encounters but no charges — review charge capture",
                resource_type="FACILITY",
                resource_id=str(facility_id),
            )
        )

    # Cash mode claims should not exist — flag if any claim tied to cash encounter via invoice path is hard; skip if schema limited

    if not signals:
        signals.append(
            FraudSignal(
                code="ALL_CLEAR",
                severity="LOW",
                title="No high-priority fraud signals",
                detail="Routine scan found no duplicate claims or high-value open invoice anomalies",
            )
        )

    high = sum(1 for s in signals if s.severity == "HIGH")
    summary = f"{len(signals)} signal(s), {high} high severity"
    return FraudRadarResponse(facility_id=facility_id, scanned_at=now.isoformat(), signals=signals, summary=summary)
