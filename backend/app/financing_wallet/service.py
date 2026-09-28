from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.adjudication.models import ClaimAdjudication
from app.claims.models import Claim
from app.audit.service import record_audit
from app.billing.models import Invoice, Payment
from app.patients.models import Person
from app.financing_wallet.models import FinancingWallet, FinancingWalletTransaction


class FinancingWalletError(ValueError):
    pass


def _money(value) -> Decimal:
    return Decimal(str(value or 0)).quantize(Decimal("0.01"))


def get_or_create_wallet(db: Session, person_id: UUID) -> FinancingWallet:
    person = db.get(Person, person_id)
    if person is None:
        raise FinancingWalletError("PERSON_NOT_FOUND")
    wallet = db.scalar(select(FinancingWallet).where(FinancingWallet.person_id == person_id))
    if wallet is None:
        wallet = FinancingWallet(person_id=person_id, currency="KES", status="ACTIVE")
        db.add(wallet)
        db.flush()
    return wallet


def _balance(db: Session, wallet_id: UUID) -> tuple[Decimal, Decimal, Decimal]:
    credit = _money(db.scalar(select(func.coalesce(func.sum(FinancingWalletTransaction.amount), 0)).where(
        FinancingWalletTransaction.wallet_id == wallet_id,
        FinancingWalletTransaction.direction == "CREDIT",
    )))
    debit = _money(db.scalar(select(func.coalesce(func.sum(FinancingWalletTransaction.amount), 0)).where(
        FinancingWalletTransaction.wallet_id == wallet_id,
        FinancingWalletTransaction.direction == "DEBIT",
    )))
    return credit - debit, credit, debit


def _pending_responsibility(db: Session, person_id: UUID) -> Decimal:
    adjudicated = _money(db.scalar(select(func.coalesce(func.sum(ClaimAdjudication.patient_amount), 0)).join(
        Claim,
        Claim.id == ClaimAdjudication.claim_id,
    ).where(
        Claim.patient_id == person_id,
        ClaimAdjudication.decision.in_({"APPROVED", "PARTIALLY_APPROVED"}),
    )))
    invoices = _money(db.scalar(select(func.coalesce(func.sum(Invoice.patient_amount), 0)).where(
        Invoice.patient_id == person_id,
        Invoice.status.in_({"OPEN", "ISSUED", "PARTIAL", "ACTIVE"}),
    )))
    payments = _money(db.scalar(select(func.coalesce(func.sum(Payment.amount), 0)).where(
        Payment.patient_id == person_id,
        Payment.status.in_({"CONFIRMED", "RECORDED", "SUCCESS", "PAID"}),
    )))
    return max(Decimal("0.00"), max(adjudicated, invoices) - payments)


def summary(db: Session, person_id: UUID, limit: int = 50) -> dict:
    wallet = get_or_create_wallet(db, person_id)
    balance, credit, debit = _balance(db, wallet.id)
    txs = list(db.scalars(select(FinancingWalletTransaction).where(
        FinancingWalletTransaction.wallet_id == wallet.id
    ).order_by(FinancingWalletTransaction.created_at.desc()).limit(max(1, min(limit, 100)))))
    return {
        "person_id": person_id,
        "wallet_id": wallet.id,
        "currency": wallet.currency,
        "status": wallet.status,
        "available_balance": balance,
        "total_contributions": credit,
        "total_applied": debit,
        "pending_patient_responsibility": _pending_responsibility(db, person_id),
        "transaction_count": len(txs),
        "transactions": [
            {
                "id": t.id, "transaction_type": t.transaction_type, "direction": t.direction,
                "amount": t.amount, "currency": t.currency, "reference": t.reference,
                "description": t.description, "source_type": t.source_type, "source_id": t.source_id,
                "invoice_id": t.invoice_id, "payer_id": t.payer_id,
                "created_at": t.created_at.isoformat() if t.created_at else datetime.now(timezone.utc).isoformat(),
            } for t in txs
        ],
    }


def contribute(db: Session, *, person_id: UUID, facility_id: UUID, amount: Decimal, reference: str | None,
               source_type: str, description: str | None, actor_user_id: UUID):
    wallet = get_or_create_wallet(db, person_id)
    ref = reference or f"FXFW-C-{datetime.now(timezone.utc):%Y%m%d}-{uuid4().hex[:12].upper()}"
    existing = db.scalar(select(FinancingWalletTransaction).where(
        FinancingWalletTransaction.wallet_id == wallet.id, FinancingWalletTransaction.reference == ref
    ))
    if existing:
        return existing
    tx = FinancingWalletTransaction(
        wallet_id=wallet.id, person_id=person_id, facility_id=facility_id,
        transaction_type="CONTRIBUTION", direction="CREDIT", amount=_money(amount),
        currency=wallet.currency, reference=ref, description=description or "Patient financing wallet contribution",
        source_type=source_type, created_by=actor_user_id,
    )
    db.add(tx)
    record_audit(db, action="FINANCING_WALLET_CONTRIBUTION", resource_type="FINANCING_WALLET",
                 resource_id=str(wallet.id), result="SUCCESS", user_id=actor_user_id, facility_id=facility_id,
                 patient_id=person_id, metadata={"amount": str(tx.amount), "reference": ref}, commit=False)
    db.commit(); db.refresh(tx)
    return tx


def apply_to_invoice(db: Session, *, person_id: UUID, facility_id: UUID, invoice_id: UUID, amount: Decimal,
                     reference: str | None, description: str | None, actor_user_id: UUID):
    wallet = get_or_create_wallet(db, person_id)
    invoice = db.get(Invoice, invoice_id)
    if invoice is None or invoice.patient_id != person_id or invoice.facility_id != facility_id:
        raise FinancingWalletError("INVOICE_ACCESS_DENIED")
    if str(invoice.status).upper() in {"PAID", "SETTLED", "CLOSED", "CANCELLED"}:
        raise FinancingWalletError("INVOICE_NOT_OPEN")
    balance, _, _ = _balance(db, wallet.id)
    amount = _money(amount)
    if amount > balance:
        raise FinancingWalletError("INSUFFICIENT_WALLET_BALANCE")

    paid = _money(db.scalar(select(func.coalesce(func.sum(Payment.amount), 0)).where(
        Payment.invoice_id == invoice.id,
        Payment.status.in_({"CONFIRMED", "RECORDED", "SUCCESS", "PAID"}),
    )))
    already_applied = _money(db.scalar(select(func.coalesce(func.sum(FinancingWalletTransaction.amount), 0)).where(
        FinancingWalletTransaction.invoice_id == invoice.id,
        FinancingWalletTransaction.direction == "DEBIT",
        FinancingWalletTransaction.wallet_id == wallet.id,
    )))
    outstanding = max(Decimal("0.00"), _money(invoice.patient_amount) - paid - already_applied)
    if amount > outstanding:
        raise FinancingWalletError("AMOUNT_EXCEEDS_PATIENT_BALANCE")
    ref = reference or f"FXFW-A-{datetime.now(timezone.utc):%Y%m%d}-{uuid4().hex[:12].upper()}"
    existing = db.scalar(select(FinancingWalletTransaction).where(
        FinancingWalletTransaction.wallet_id == wallet.id, FinancingWalletTransaction.reference == ref
    ))
    if existing:
        return existing
    tx = FinancingWalletTransaction(
        wallet_id=wallet.id, person_id=person_id, facility_id=facility_id, invoice_id=invoice.id,
        payer_id=invoice.payer_id, transaction_type="PATIENT_INVOICE_PAYMENT", direction="DEBIT",
        amount=amount, currency=wallet.currency, reference=ref,
        description=description or f"Wallet payment against invoice {invoice.invoice_id}",
        source_type="WALLET", source_id=str(invoice.id), created_by=actor_user_id,
    )
    db.add(tx)
    remaining = outstanding - amount
    if remaining <= 0:
        invoice.status = "PAID"
    elif paid + already_applied + amount > 0:
        invoice.status = "PARTIAL"
    record_audit(db, action="FINANCING_WALLET_APPLY", resource_type="FINANCING_WALLET",
                 resource_id=str(wallet.id), result="SUCCESS", user_id=actor_user_id, facility_id=facility_id,
                 patient_id=person_id, metadata={"invoice_id": str(invoice.id), "amount": str(amount), "reference": ref}, commit=False)
    db.commit(); db.refresh(tx)
    return tx


def reconcile_patient_responsibility(db: Session, *, person_id: UUID, facility_id: UUID, actor_user_id: UUID):
    result = summary(db, person_id)
    record_audit(db, action="FINANCING_WALLET_RECONCILE", resource_type="FINANCING_WALLET",
                 resource_id=str(result["wallet_id"]), result="SUCCESS", user_id=actor_user_id,
                 facility_id=facility_id, patient_id=person_id,
                 metadata={"pending_patient_responsibility": str(result["pending_patient_responsibility"])}, commit=True)
    return result
