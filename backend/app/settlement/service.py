from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.adjudication.models import ClaimAdjudication
from app.audit.service import record_audit
from app.billing.models import Invoice
from app.claims.models import Claim
from app.settlement.models import (
    ProviderPayment,
    SettlementBatch,
    SettlementLedgerEntry,
    SettlementObligation,
    SettlementReconciliation,
)


class SettlementError(ValueError):
    pass


def _money(v):
    return Decimal(str(v or 0)).quantize(Decimal("0.01"))


def generate_obligation(db: Session, *, claim_id, facility_id, actor_user_id):
    claim = db.get(Claim, claim_id)
    if claim is None:
        raise SettlementError("CLAIM_NOT_FOUND")
    invoice = db.get(Invoice, claim.invoice_id)
    if invoice is None or invoice.facility_id != facility_id:
        raise SettlementError("FACILITY_ACCESS_DENIED")
    adj = db.scalar(select(ClaimAdjudication).where(ClaimAdjudication.claim_id == claim.id))
    if adj is None:
        raise SettlementError("CLAIM_NOT_ADJUDICATED")
    if adj.decision == "DENIED" or _money(adj.allowed_amount) <= 0:
        raise SettlementError("NOT_PAYABLE")
    existing = db.scalar(select(SettlementObligation).where(SettlementObligation.claim_id == claim.id))
    if existing:
        return existing
    obligation = SettlementObligation(
        obligation_number=f"FXOB-{datetime.now(timezone.utc):%Y%m%d}-{uuid4().hex[:10].upper()}",
        claim_id=claim.id,
        facility_id=facility_id,
        payer_id=claim.payer_id,
        submitted_amount=_money(adj.submitted_amount),
        payable_amount=_money(adj.allowed_amount),
        patient_amount=_money(adj.patient_amount),
        status="READY",
    )
    db.add(obligation)
    db.flush()
    record_audit(
        db,
        action="CREATE_SETTLEMENT_OBLIGATION",
        resource_type="SETTLEMENT_OBLIGATION",
        resource_id=str(obligation.id),
        result="SUCCESS",
        user_id=actor_user_id,
        facility_id=facility_id,
        metadata={"claim_id": str(claim.id), "amount": str(obligation.payable_amount)},
        commit=False,
    )
    db.commit()
    db.refresh(obligation)
    return obligation


def create_batch(db: Session, *, facility_id, payer_id, actor_user_id):
    obligations = list(
        db.scalars(
            select(SettlementObligation)
            .where(
                SettlementObligation.facility_id == facility_id,
                SettlementObligation.payer_id == payer_id,
                SettlementObligation.status == "READY",
            )
            .order_by(SettlementObligation.created_at)
        ).all()
    )
    if not obligations:
        raise SettlementError("NO_READY_OBLIGATIONS")
    total = sum((_money(o.payable_amount) for o in obligations), Decimal("0.00"))
    batch = SettlementBatch(
        batch_number=f"FXSB-{datetime.now(timezone.utc):%Y%m%d}-{uuid4().hex[:10].upper()}",
        facility_id=facility_id,
        payer_id=payer_id,
        total_amount=total,
        status="OPEN",
    )
    db.add(batch)
    db.flush()
    for o in obligations:
        o.status = "IN_BATCH"
        o.batch_id = batch.id
    record_audit(
        db,
        action="CREATE_SETTLEMENT_BATCH",
        resource_type="SETTLEMENT_BATCH",
        resource_id=str(batch.id),
        result="SUCCESS",
        user_id=actor_user_id,
        facility_id=facility_id,
        metadata={"count": len(obligations), "total": str(total)},
        commit=False,
    )
    db.commit()
    db.refresh(batch)
    return batch


def record_payment(db: Session, *, batch_id, facility_id, payload, actor_user_id):
    batch = db.get(SettlementBatch, batch_id)
    if batch is None or batch.facility_id != facility_id:
        raise SettlementError("BATCH_NOT_FOUND")
    obligation = db.get(SettlementObligation, payload.obligation_id)
    if obligation is None or obligation.facility_id != facility_id:
        raise SettlementError("OBLIGATION_NOT_FOUND")
    amount = _money(payload.amount)
    if amount <= 0:
        raise SettlementError("INVALID_PAYMENT_AMOUNT")
    payment = ProviderPayment(
        payment_number=f"FXPP-{datetime.now(timezone.utc):%Y%m%d}-{uuid4().hex[:10].upper()}",
        facility_id=facility_id,
        batch_id=batch.id,
        obligation_id=obligation.id,
        amount=amount,
        method=payload.method,
        external_reference=getattr(payload, "external_reference", None),
        status="RECORDED",
    )
    db.add(payment)
    db.flush()
    obligation.status = "PAID"
    record_audit(
        db,
        action="RECORD_PROVIDER_PAYMENT",
        resource_type="PROVIDER_PAYMENT",
        resource_id=str(payment.id),
        result="SUCCESS",
        user_id=actor_user_id,
        facility_id=facility_id,
        metadata={"amount": str(amount), "batch_id": str(batch.id)},
        commit=False,
    )
    db.commit()
    db.refresh(payment)
    return payment


def reconcile_batch(db: Session, *, batch_id, facility_id, received_amount, actor_user_id):
    batch = db.get(SettlementBatch, batch_id)
    if batch is None or batch.facility_id != facility_id:
        raise SettlementError("BATCH_NOT_FOUND")
    received = _money(received_amount)
    expected = _money(batch.total_amount)
    variance = (received - expected).quantize(Decimal("0.01"))
    rec = SettlementReconciliation(
        batch_id=batch.id,
        facility_id=facility_id,
        expected_amount=expected,
        received_amount=received,
        variance_amount=variance,
        status="MATCHED" if variance == 0 else "VARIANCE",
    )
    db.add(rec)
    batch.status = "RECONCILED"
    db.add(
        SettlementLedgerEntry(
            facility_id=facility_id,
            batch_id=batch.id,
            entry_type="RECONCILIATION",
            amount=received,
            metadata_json={"variance": str(variance)},
        )
    )
    record_audit(
        db,
        action="RECONCILE_SETTLEMENT_BATCH",
        resource_type="SETTLEMENT_BATCH",
        resource_id=str(batch.id),
        result=rec.status,
        user_id=actor_user_id,
        facility_id=facility_id,
        metadata={"received": str(received), "expected": str(expected), "variance": str(variance)},
        commit=False,
    )
    db.commit()
    db.refresh(rec)
    return rec
