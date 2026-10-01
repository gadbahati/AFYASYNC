from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from statistics import mean
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.billing.models import Invoice, Payment
from app.claims.models import Claim
from app.revenue_anomaly.models import RevenueAnomalyCase
from app.settlement.models import SettlementObligation

# RevenueRecoveryCase is imported lazily below to keep this module compatible with
# deployments where the settlement package is initialized before recovery models.


def _money(value) -> Decimal:
    return Decimal(str(value or 0)).quantize(Decimal("0.01"))


def _days(value: int) -> int:
    return max(7, min(int(value or 90), 365))


def _date_floor(days: int):
    return datetime.now(timezone.utc) - timedelta(days=days)


def financial_overview(db: Session, facility_id: UUID, days: int = 90) -> dict:
    days = _days(days)
    since = _date_floor(days)

    billed = _money(db.scalar(select(func.coalesce(func.sum(Invoice.total_amount), 0)).where(
        Invoice.facility_id == facility_id, Invoice.created_at >= since
    )))
    payer_billed = _money(db.scalar(select(func.coalesce(func.sum(Invoice.payer_amount), 0)).where(
        Invoice.facility_id == facility_id, Invoice.created_at >= since
    )))
    patient_billed = _money(db.scalar(select(func.coalesce(func.sum(Invoice.patient_amount), 0)).where(
        Invoice.facility_id == facility_id, Invoice.created_at >= since
    )))
    collected = _money(db.scalar(select(func.coalesce(func.sum(Payment.amount), 0)).where(
        Payment.facility_id == facility_id,
        Payment.created_at >= since,
        Payment.status.in_(["CONFIRMED", "SUCCESS", "COMPLETED", "RECORDED"])
    )))

    claims_submitted = _money(db.scalar(select(func.coalesce(func.sum(Claim.claim_amount), 0)).where(
        Claim.invoice_id.in_(select(Invoice.id).where(Invoice.facility_id == facility_id)),
        Claim.updated_at >= since
    )))
    claims_paid = _money(db.scalar(select(func.coalesce(func.sum(Claim.paid_amount), 0)).where(
        Claim.invoice_id.in_(select(Invoice.id).where(Invoice.facility_id == facility_id)),
        Claim.updated_at >= since
    )))
    receivables = max(Decimal("0"), claims_submitted - claims_paid)

    anomaly = db.execute(select(
        func.count(RevenueAnomalyCase.id),
        func.coalesce(func.sum(RevenueAnomalyCase.amount_at_risk), 0)
    ).where(
        RevenueAnomalyCase.facility_id == facility_id,
        RevenueAnomalyCase.status.in_(["OPEN", "IN_REVIEW", "CONFIRMED"])
    )).one()

    try:
        from app.settlement.recovery import RevenueRecoveryCase
        recovery = db.execute(select(
            func.count(RevenueRecoveryCase.id),
            func.coalesce(func.sum(RevenueRecoveryCase.outstanding_amount), 0)
        ).where(
            RevenueRecoveryCase.facility_id == facility_id,
            RevenueRecoveryCase.status.in_(["OPEN", "IN_PROGRESS", "DISPUTED"])
        )).one()
        recovery_cases, recovery_outstanding = int(recovery[0]), _money(recovery[1])
    except Exception:
        recovery_cases, recovery_outstanding = 0, Decimal("0")

    return {
        "window_days": days,
        "billed": float(billed),
        "payer_billed": float(payer_billed),
        "patient_billed": float(patient_billed),
        "collected": float(collected),
        "collection_rate": round(float((collected / billed * 100) if billed else 0), 2),
        "claims_submitted": float(claims_submitted),
        "claims_paid": float(claims_paid),
        "claims_receivable": float(receivables),
        "anomaly_cases": int(anomaly[0] or 0),
        "anomaly_amount_at_risk": float(_money(anomaly[1])),
        "recovery_cases": recovery_cases,
        "recovery_outstanding": float(recovery_outstanding),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def forecast(db: Session, facility_id: UUID, history_days: int = 90) -> dict:
    history_days = _days(history_days)
    since = _date_floor(history_days)
    now = datetime.now(timezone.utc)

    # Daily billing/collection series gives a transparent baseline forecast.
    invoice_rows = db.execute(select(Invoice.created_at, Invoice.total_amount).where(
        Invoice.facility_id == facility_id, Invoice.created_at >= since
    )).all()
    payment_rows = db.execute(select(Payment.created_at, Payment.amount).where(
        Payment.facility_id == facility_id,
        Payment.created_at >= since,
        Payment.status.in_(["CONFIRMED", "SUCCESS", "COMPLETED", "RECORDED"])
    )).all()

    billing_by_day: dict[str, Decimal] = {}
    cash_by_day: dict[str, Decimal] = {}
    for created, amount in invoice_rows:
        key = (created or now).date().isoformat()
        billing_by_day[key] = billing_by_day.get(key, Decimal("0")) + _money(amount)
    for created, amount in payment_rows:
        key = (created or now).date().isoformat()
        cash_by_day[key] = cash_by_day.get(key, Decimal("0")) + _money(amount)

    daily_billing = [float(billing_by_day.get((now - timedelta(days=i)).date().isoformat(), 0)) for i in range(history_days)]
    daily_cash = [float(cash_by_day.get((now - timedelta(days=i)).date().isoformat(), 0)) for i in range(history_days)]

    active_days = max(1, min(history_days, 30))
    billing_run_rate = mean(daily_billing[:active_days]) if daily_billing else 0
    cash_run_rate = mean(daily_cash[:active_days]) if daily_cash else 0

    # A conservative forecast: recent run-rate, not a claim of guaranteed revenue.
    periods = {}
    for horizon in (30, 60, 90):
        periods[str(horizon)] = {
            "projected_billing": round(billing_run_rate * horizon, 2),
            "projected_cash_collection": round(cash_run_rate * horizon, 2),
            "projected_net_cash": round((cash_run_rate - billing_run_rate) * horizon, 2),
        }

    volatility = 0
    if daily_cash:
        avg = mean(daily_cash)
        if avg:
            volatility = round((sum((x - avg) ** 2 for x in daily_cash) / len(daily_cash)) ** 0.5 / avg * 100, 2)

    return {
        "history_days": history_days,
        "recent_window_days": active_days,
        "daily_billing_run_rate": round(billing_run_rate, 2),
        "daily_cash_run_rate": round(cash_run_rate, 2),
        "cash_volatility_percent": volatility,
        "forecast": periods,
        "method": "30-day recent daily run-rate baseline; excludes unverified external funding and does not guarantee future collections.",
        "generated_at": now.isoformat(),
    }


def payer_performance(db: Session, facility_id: UUID, days: int = 90) -> list[dict]:
    since = _date_floor(_days(days))
    rows = db.execute(
        select(
            Claim.payer_id,
            func.count(Claim.id),
            func.coalesce(func.sum(Claim.claim_amount), 0),
            func.coalesce(func.sum(Claim.approved_amount), 0),
            func.coalesce(func.sum(Claim.paid_amount), 0),
        ).join(Invoice, Invoice.id == Claim.invoice_id).where(
            Invoice.facility_id == facility_id, Claim.updated_at >= since
        ).group_by(Claim.payer_id).order_by(func.sum(Claim.claim_amount).desc())
    ).all()

    result = []
    for payer_id, count, submitted, approved, paid in rows:
        submitted_d, approved_d, paid_d = map(_money, (submitted, approved, paid))
        result.append({
            "payer_id": str(payer_id),
            "claims": int(count),
            "submitted": float(submitted_d),
            "approved": float(approved_d),
            "paid": float(paid_d),
            "approval_rate": round(float(approved_d / submitted_d * 100) if submitted_d else 0, 2),
            "collection_rate": round(float(paid_d / approved_d * 100) if approved_d else 0, 2),
            "outstanding": float(max(Decimal("0"), approved_d - paid_d)),
        })
    return result
