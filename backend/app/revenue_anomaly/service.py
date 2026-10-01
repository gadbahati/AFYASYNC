from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from math import sqrt
from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.audit.service import record_audit
from app.billing.models import Charge, Invoice, InvoiceItem
from app.claims.models import Claim, ClaimItem
from app.encounters.models import Encounter
from app.revenue_anomaly.models import RevenueAnomalyCase, RevenueAnomalyEvent
from app.settlement.models import SettlementBatch, SettlementReconciliation


class RevenueAnomalyError(ValueError):
    pass


def _money(value) -> Decimal:
    return Decimal(str(value or 0)).quantize(Decimal("0.01"))


def _severity(score: int) -> str:
    if score >= 85:
        return "CRITICAL"
    if score >= 70:
        return "HIGH"
    if score >= 50:
        return "MEDIUM"
    return "LOW"


def _active_case(db: Session, fingerprint: str):
    return db.scalar(
        select(RevenueAnomalyCase)
        .where(
            RevenueAnomalyCase.fingerprint == fingerprint,
            RevenueAnomalyCase.status.in_([ "OPEN", "IN_REVIEW", "CONFIRMED" ]),
        )
        .limit(1)
    )


def _create_case(db: Session, *, facility_id: UUID, anomaly_type: str, score: int,
                 claim_id: UUID | None, invoice_id: UUID | None, patient_id: UUID | None,
                 payer_id: UUID | None, amount: Decimal, fingerprint: str,
                 summary: str, evidence: dict, actor_id: UUID | None = None):
    existing = _active_case(db, fingerprint)
    if existing:
        return existing, False
    case = RevenueAnomalyCase(
        case_number=f"RVA-{datetime.now(timezone.utc):%Y%m%d}-{uuid4().hex[:10].upper()}",
        facility_id=facility_id,
        anomaly_type=anomaly_type,
        severity=_severity(score),
        risk_score=max(0, min(100, score)),
        status="OPEN",
        claim_id=claim_id,
        invoice_id=invoice_id,
        patient_id=patient_id,
        payer_id=payer_id,
        amount_at_risk=max(Decimal("0"), amount),
        fingerprint=fingerprint,
        summary=summary,
        evidence=evidence,
    )
    db.add(case)
    db.flush()
    db.add(RevenueAnomalyEvent(case_id=case.id, action="OPENED", status="OPEN", metadata_json=evidence, actor_id=actor_id))
    return case, True


def scan_facility(db: Session, *, facility_id: UUID, days: int = 30, actor_id: UUID | None = None) -> dict:
    days = max(7, min(days, 90))
    since = datetime.now(timezone.utc) - timedelta(days=days)

    claim_rows = list(
        db.execute(
            select(Claim, Encounter, Invoice)
            .join(Encounter, Encounter.id == Claim.encounter_id)
            .join(Invoice, Invoice.id == Claim.invoice_id)
            .where(Encounter.facility_id == facility_id, Claim.updated_at >= since)
            .order_by(Claim.updated_at.desc())
            .limit(3000)
        ).all()
    )

    signals: list[dict] = []
    opened = 0
    by_patient_day_amount: dict[tuple, list] = defaultdict(list)
    amounts: list[float] = []

    for claim, enc, invoice in claim_rows:
        amount = _money(claim.claim_amount)
        amounts.append(float(amount))
        event_date = (claim.submitted_at or claim.updated_at or datetime.now(timezone.utc)).date().isoformat()
        by_patient_day_amount[(claim.patient_id, event_date, amount)].append((claim, enc, invoice))

        invoice_total = _money(invoice.total_amount)
        diff = abs(amount - invoice_total)
        if diff > Decimal("0.01"):
            pct = float(diff / max(invoice_total, Decimal("1")) * Decimal("100"))
            score = 60 if pct >= 10 else 50
            case, created = _create_case(
                db, facility_id=facility_id, anomaly_type="CLAIM_INVOICE_MISMATCH", score=score,
                claim_id=claim.id, invoice_id=invoice.id, patient_id=claim.patient_id,
                payer_id=claim.payer_id, amount=diff, fingerprint=f"CLAIM_INVOICE_MISMATCH:{claim.id}",
                summary=f"Claim amount differs from invoice total by KES {diff:.2f}.",
                evidence={"claim_amount": float(amount), "invoice_total": float(invoice_total), "difference": float(diff), "difference_percent": round(pct, 2)},
                actor_id=actor_id,
            )
            if created: signals.append({"type":"CLAIM_INVOICE_MISMATCH","case_id":str(case.id),"risk_score":case.risk_score}); opened += int(created)

    for (patient_id, day, amount), rows in by_patient_day_amount.items():
        if len(rows) >= 2 and amount > 0:
            claim_ids = [str(r[0].id) for r in rows[:10]]
            score = 90 if len(rows) >= 3 else 80
            case, created = _create_case(
                db, facility_id=facility_id, anomaly_type="DUPLICATE_CLAIM", score=score,
                claim_id=rows[0][0].id, invoice_id=rows[0][2].id, patient_id=patient_id,
                payer_id=rows[0][0].payer_id, amount=amount * len(rows),
                fingerprint=f"DUPLICATE_CLAIM:{patient_id}:{day}:{amount}",
                summary=f"{len(rows)} claims share patient, date and amount.",
                evidence={"patient_id":str(patient_id),"date":day,"claim_ids":claim_ids,"claim_count":len(rows),"amount_each":float(amount)},
                actor_id=actor_id,
            )
            if created: signals.append({"type":"DUPLICATE_CLAIM","case_id":str(case.id),"risk_score":case.risk_score}); opened += int(created)

    if len(amounts) >= 8:
        mean = sum(amounts) / len(amounts)
        variance = sum((v - mean) ** 2 for v in amounts) / len(amounts)
        std = sqrt(variance)
        if std > 0:
            for claim, enc, invoice in claim_rows:
                z = (float(_money(claim.claim_amount)) - mean) / std
                if z >= 3:
                    score = 85 if z >= 4 else 72
                    case, created = _create_case(
                        db, facility_id=facility_id, anomaly_type="HIGH_AMOUNT_OUTLIER", score=score,
                        claim_id=claim.id, invoice_id=invoice.id, patient_id=claim.patient_id,
                        payer_id=claim.payer_id, amount=_money(claim.claim_amount),
                        fingerprint=f"HIGH_AMOUNT_OUTLIER:{claim.id}",
                        summary=f"Claim amount is {z:.1f} standard deviations above the facility window mean.",
                        evidence={"claim_amount":float(_money(claim.claim_amount)),"mean":round(mean,2),"std_dev":round(std,2),"z_score":round(z,2)},
                        actor_id=actor_id,
                    )
                    if created: signals.append({"type":"HIGH_AMOUNT_OUTLIER","case_id":str(case.id),"risk_score":case.risk_score}); opened += int(created)

    claim_ids = [c.id for c, _, _ in claim_rows]
    if claim_ids:
        line_totals = dict(
            db.execute(
                select(ClaimItem.claim_id, func.coalesce(func.sum(ClaimItem.amount), 0))
                .where(ClaimItem.claim_id.in_(claim_ids))
                .group_by(ClaimItem.claim_id)
            ).all()
        )
        for claim, enc, invoice in claim_rows:
            line_total = _money(line_totals.get(claim.id, 0))
            amount = _money(claim.claim_amount)
            diff = abs(line_total - amount)
            if diff > Decimal("0.01"):
                case, created = _create_case(
                    db, facility_id=facility_id, anomaly_type="CLAIM_LINE_TOTAL_MISMATCH", score=65,
                    claim_id=claim.id, invoice_id=invoice.id, patient_id=claim.patient_id,
                    payer_id=claim.payer_id, amount=diff, fingerprint=f"CLAIM_LINE_TOTAL_MISMATCH:{claim.id}",
                    summary=f"Claim lines total KES {line_total:.2f} versus claim total KES {amount:.2f}.",
                    evidence={"line_total":float(line_total),"claim_amount":float(amount),"difference":float(diff)},
                    actor_id=actor_id,
                )
                if created: signals.append({"type":"CLAIM_LINE_TOTAL_MISMATCH","case_id":str(case.id),"risk_score":case.risk_score}); opened += int(created)

    charge_rows = list(
        db.execute(
            select(Charge)
            .where(Charge.facility_id == facility_id, Charge.created_at >= since, Charge.status == "ACTIVE")
            .order_by(Charge.created_at.desc())
            .limit(5000)
        ).scalars().all()
    )
    by_charge_key: dict[tuple, list] = defaultdict(list)
    for charge in charge_rows:
        day = (charge.created_at or datetime.now(timezone.utc)).date().isoformat()
        by_charge_key[(charge.patient_id, charge.service_id, day, _money(charge.total_amount))].append(charge)
    for key, rows in by_charge_key.items():
        if len(rows) >= 2 and key[3] > 0:
            patient_id, service_id, day, amount = key
            case, created = _create_case(
                db, facility_id=facility_id, anomaly_type="DUPLICATE_CHARGE", score=78,
                claim_id=None, invoice_id=None, patient_id=patient_id, payer_id=None,
                amount=amount * len(rows), fingerprint=f"DUPLICATE_CHARGE:{patient_id}:{service_id}:{day}:{amount}",
                summary=f"{len(rows)} identical active charges for one patient/service/day.",
                evidence={"charge_ids":[str(x.id) for x in rows[:10]],"service_id":str(service_id),"date":day,"amount_each":float(amount)},
                actor_id=actor_id,
            )
            if created: signals.append({"type":"DUPLICATE_CHARGE","case_id":str(case.id),"risk_score":case.risk_score}); opened += int(created)

    reconciliation_rows = list(
        db.execute(
            select(SettlementReconciliation, SettlementBatch)
            .join(SettlementBatch, SettlementBatch.id == SettlementReconciliation.batch_id)
            .where(SettlementBatch.facility_id == facility_id, SettlementReconciliation.recovery_status == "OPEN")
            .limit(1000)
        ).all()
    )
    underpayments = 0
    for rec, batch in reconciliation_rows:
        if rec.difference < 0:
            shortfall = abs(_money(rec.difference))
            case, created = _create_case(
                db, facility_id=facility_id, anomaly_type="SETTLEMENT_UNDERPAYMENT", score=82,
                claim_id=None, invoice_id=None, patient_id=None, payer_id=batch.payer_id,
                amount=shortfall, fingerprint=f"SETTLEMENT_UNDERPAYMENT:{rec.id}",
                summary=f"Settlement batch is underpaid by KES {shortfall:.2f}.",
                evidence={"reconciliation_id":str(rec.id),"batch_id":str(batch.id),"expected":float(_money(rec.expected_amount)),"received":float(_money(rec.received_amount)),"shortfall":float(shortfall)},
                actor_id=actor_id,
            )
            if created:
                underpayments += 1
                signals.append({"type":"SETTLEMENT_UNDERPAYMENT","case_id":str(case.id),"risk_score":case.risk_score})

    db.commit()
    return {
        "facility_id":str(facility_id),
        "window_days":days,
        "claims_scanned":len(claim_rows),
        "charges_scanned":len(charge_rows),
        "underpayments_scanned":len(reconciliation_rows),
        "cases_opened":opened + underpayments,
        "signals":signals[:200],
        "generated_at":datetime.now(timezone.utc).isoformat(),
        "disclaimer":"Anomalies are investigative signals, not automatic findings of fraud or wrongdoing.",
    }


def overview(db: Session, facility_id: UUID) -> dict:
    rows = db.execute(
        select(
            func.count(RevenueAnomalyCase.id),
            func.coalesce(func.sum(RevenueAnomalyCase.amount_at_risk), 0),
        ).where(
            RevenueAnomalyCase.facility_id == facility_id,
            RevenueAnomalyCase.status.in_([ "OPEN", "IN_REVIEW", "CONFIRMED" ]),
        )
    ).one()
    by_severity = dict(
        db.execute(
            select(RevenueAnomalyCase.severity, func.count())
            .where(RevenueAnomalyCase.facility_id == facility_id, RevenueAnomalyCase.status.in_([ "OPEN", "IN_REVIEW", "CONFIRMED" ]))
            .group_by(RevenueAnomalyCase.severity)
        ).all()
    )
    return {"open_cases":int(rows[0]),"amount_at_risk":float(rows[1] or 0),"by_severity":{str(k):int(v) for k,v in by_severity.items()}}


def list_cases(db: Session, facility_id: UUID, status: str | None = None):
    stmt = select(RevenueAnomalyCase).where(RevenueAnomalyCase.facility_id == facility_id).order_by(RevenueAnomalyCase.created_at.desc()).limit(500)
    if status:
        stmt = stmt.where(RevenueAnomalyCase.status == status)
    return db.scalars(stmt).all()


def update_case(db: Session, *, case_id: UUID, facility_id: UUID, status: str, note: str | None, actor_id: UUID):
    case = db.scalar(select(RevenueAnomalyCase).where(RevenueAnomalyCase.id == case_id, RevenueAnomalyCase.facility_id == facility_id))
    if not case:
        raise RevenueAnomalyError("ANOMALY_CASE_NOT_FOUND")
    allowed = {"OPEN","IN_REVIEW","CONFIRMED","DISMISSED","RESOLVED"}
    if status not in allowed:
        raise RevenueAnomalyError("INVALID_ANOMALY_STATUS")
    case.status = status
    case.notes = note
    if status in {"DISMISSED","RESOLVED"}:
        case.resolved_at = datetime.now(timezone.utc)
    db.add(RevenueAnomalyEvent(case_id=case.id, action="STATUS_CHANGED", status=status, note=note, actor_id=actor_id))
    record_audit(db, action="UPDATE_REVENUE_ANOMALY", resource_type="revenue_anomaly_case", result="SUCCESS", user_id=actor_id, facility_id=facility_id, resource_id=str(case.id), metadata={"status":status,"anomaly_type":case.anomaly_type}, commit=False)
    db.commit()
    db.refresh(case)
    return case


def case_events(db: Session, *, case_id: UUID, facility_id: UUID):
    exists = db.scalar(select(RevenueAnomalyCase.id).where(RevenueAnomalyCase.id == case_id, RevenueAnomalyCase.facility_id == facility_id))
    if not exists:
        raise RevenueAnomalyError("ANOMALY_CASE_NOT_FOUND")
    return db.scalars(select(RevenueAnomalyEvent).where(RevenueAnomalyEvent.case_id == case_id).order_by(RevenueAnomalyEvent.created_at.asc())).all()
