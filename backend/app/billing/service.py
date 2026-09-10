from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.billing.models import Charge, Invoice, InvoiceItem, Payment, Service
from app.encounters.models import Encounter


class BillingError(ValueError):
    pass


def _invoice_number(db: Session) -> str:
    sequence = db.scalar(text("nextval('afasync_invoice_seq')"))
    return f"INV-{datetime.now(timezone.utc):%Y%m%d}-{int(sequence):05d}"


def create_charge(db: Session, facility_id: UUID, payload: dict) -> Charge:
    encounter = db.get(Encounter, payload["encounter_id"])
    if encounter is None:
        raise BillingError("ENCOUNTER_NOT_FOUND")
    if encounter.facility_id != facility_id:
        raise BillingError("FACILITY_ACCESS_DENIED")
    service = db.get(Service, payload["service_id"])
    if service is None or service.status != "ACTIVE":
        raise BillingError("SERVICE_NOT_FOUND")
    if service.facility_id != facility_id:
        raise BillingError("FACILITY_ACCESS_DENIED")
    quantity = Decimal(str(payload["quantity"]))
    if quantity <= 0:
        raise BillingError("INVALID_QUANTITY")
    unit_price = Decimal(str(service.price))
    total = quantity * unit_price
    charge = Charge(charge_id=f"CHG-{uuid4().hex[:20].upper()}", encounter_id=encounter.id, patient_id=encounter.patient_id, facility_id=facility_id, service_id=service.id, quantity=quantity, unit_price=unit_price, total_amount=total, source_type=payload["source_type"], source_id=payload.get("source_id"))
    db.add(charge)
    db.commit()
    db.refresh(charge)
    return charge


def create_invoice(db: Session, facility_id: UUID, encounter_id: UUID) -> Invoice:
    encounter = db.get(Encounter, encounter_id)
    if encounter is None:
        raise BillingError("ENCOUNTER_NOT_FOUND")
    if encounter.facility_id != facility_id:
        raise BillingError("FACILITY_ACCESS_DENIED")
    existing = db.scalar(select(Invoice).where(Invoice.encounter_id == encounter.id, Invoice.facility_id == facility_id, Invoice.status.not_in(["VOID", "CANCELLED"])).limit(1))
    if existing is not None:
        raise BillingError("INVOICE_ALREADY_EXISTS")
    charges = list(db.scalars(select(Charge).where(Charge.encounter_id == encounter.id, Charge.facility_id == facility_id, Charge.status == "ACTIVE")))
    if not charges:
        raise BillingError("NO_CHARGES")
    subtotal = sum((Decimal(str(c.total_amount)) for c in charges), Decimal("0"))
    invoice = Invoice(invoice_id=_invoice_number(db), patient_id=encounter.patient_id, facility_id=facility_id, encounter_id=encounter.id, subtotal=subtotal, payer_amount=Decimal("0"), patient_amount=subtotal, total_amount=subtotal)
    db.add(invoice)
    db.flush()
    for charge in charges:
        db.add(InvoiceItem(invoice_id=invoice.id, charge_id=charge.id, description=f"Service {charge.service_id}", quantity=charge.quantity, unit_price=charge.unit_price, amount=charge.total_amount))
    db.commit()
    db.refresh(invoice)
    return invoice


def record_payment(db: Session, facility_id: UUID, payload: dict) -> Payment:
    invoice = db.get(Invoice, payload["invoice_id"])
    if invoice is None:
        raise BillingError("INVOICE_NOT_FOUND")
    if invoice.facility_id != facility_id:
        raise BillingError("FACILITY_ACCESS_DENIED")
    if invoice.status == "PAID":
        raise BillingError("INVOICE_ALREADY_PAID")
    amount = Decimal(str(payload["amount"]))
    if amount <= 0:
        raise BillingError("INVALID_PAYMENT_AMOUNT")

    idempotency_key = payload.get("idempotency_key")
    transaction_id = f"AFY-TXN-{idempotency_key}" if idempotency_key else f"AFY-TXN-{uuid4().hex.upper()}"
    existing = db.scalar(select(Payment).where(Payment.transaction_id == transaction_id).limit(1))
    if existing is not None:
        if existing.invoice_id != invoice.id or Decimal(str(existing.amount)) != amount:
            raise BillingError("IDEMPOTENCY_KEY_REUSED")
        return existing

    paid = sum((Decimal(str(p.amount)) for p in db.scalars(select(Payment).where(Payment.invoice_id == invoice.id, Payment.status == "CONFIRMED"))), Decimal("0"))
    balance = Decimal(str(invoice.patient_amount)) - paid
    if amount > balance:
        raise BillingError("PAYMENT_EXCEEDS_BALANCE")
    payment = Payment(transaction_id=transaction_id, invoice_id=invoice.id, patient_id=invoice.patient_id, facility_id=facility_id, amount=amount, payment_method=payload["payment_method"], provider=payload.get("provider"), external_reference=payload.get("external_reference"), status="CONFIRMED", confirmed_at=datetime.now(timezone.utc))
    db.add(payment)
    db.flush()
    new_paid = paid + amount
    invoice.status = "PAID" if new_paid == Decimal(str(invoice.patient_amount)) else "PARTIALLY_PAID"
    db.commit()
    db.refresh(payment)
    return payment
