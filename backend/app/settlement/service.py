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
        created_by=actor_user_id,
    )
    db.add(batch)
    db.flush()
    for o in obligations:
        o.status = "IN_BATCH"
    record_audit(
        db,
        action="CREATE_SETTLEMENT_BATCH",
        resource_type="SETTLEMENT_BATCH",
        resource_id=str(batch.id),
        result="SUCCESS",
        user_id=actor_user_id,
        facility_id=facility_id,
        metadata={"obligation_count": len(obligations), "amount": str(batch.total_amount)},
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
    if obligation.status not in {"IN_BATCH", "READY"}:
        raise SettlementError("OBLIGATION_NOT_PAYABLE")
    existing = db.scalar(select(ProviderPayment).where(ProviderPayment.obligation_id == obligation.id))
    if existing:
        return existing
    amount = _money(payload.amount)
    if amount != _money(obligation.payable_amount):
        raise SettlementError("PAYMENT_AMOUNT_MISMATCH")
    payment = ProviderPayment(
        payment_reference=f"FXPP-{datetime.now(timezone.utc):%Y%m%d}-{uuid4().hex[:10].upper()}",
        batch_id=batch.id,
        obligation_id=obligation.id,
        facility_id=facility_id,
        payer_id=batch.payer_id,
        amount=amount,
        method=payload.method,
        external_reference=payload.external_reference,
        status="RECORDED",
    )
    db.add(payment)
    obligation.status = "SETTLED"
    db.add(
        SettlementLedgerEntry(
            batch_id=batch.id,
            obligation_id=obligation.id,
            entry_type="PROVIDER_PAYMENT",
            debit_amount=Decimal("0"),
            credit_amount=amount,
            reference=payment.payment_reference,
        )
    )
    claim = db.get(Claim, obligation.claim_id)
    if claim is not None:
        claim.paid_amount = _money(claim.paid_amount) + amount
    record_audit(
        db,
        action="RECORD_PROVIDER_PAYMENT",
        resource_type="PROVIDER_PAYMENT",
        resource_id=str(payment.id),
        result="SUCCESS",
        user_id=actor_user_id,
        facility_id=facility_id,
        metadata={"batch_id": str(batch.id), "amount": str(amount)},
        commit=False,
    )
    db.commit()
    db.refresh(payment)
    return payment


def reconcile_batch(db: Session, *, batch_id, facility_id, received_amount, actor_user_id):
    batch = db.get(SettlementBatch, batch_id)
    if batch is None or batch.facility_id != facility_id:
        raise SettlementError("BATCH_NOT_FOUND")
    expected = _money(batch.total_amount)
    received = _money(received_amount)
    diff = received - expected
    status = "RECONCILED" if diff == 0 else "VARIANCE"
    variance_type = "NONE" if diff == 0 else ("UNDERPAYMENT" if diff < 0 else "OVERPAYMENT")
    row = SettlementReconciliation(
        batch_id=batch.id,
        expected_amount=expected,
        received_amount=received,
        difference=diff,
        status=status,
        variance_type=variance_type,
        reconciled_by=actor_user_id,
        reconciled_at=datetime.now(timezone.utc),
        recovery_status="NOT_REQUIRED" if diff >= 0 else "OPEN",
    )
    db.add(row)
    batch.status = "RECONCILED" if diff == 0 else "PARTIAL"
    record_audit(
        db,
        action="RECONCILE_SETTLEMENT_BATCH",
        resource_type="SETTLEMENT_BATCH",
        resource_id=str(batch.id),
        result="SUCCESS",
        user_id=actor_user_id,
        facility_id=facility_id,
        metadata={"expected": str(expected), "received": str(received), "difference": str(diff)},
        commit=False,
    )
    db.commit()
    db.refresh(row)
    return row
