from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.audit.service import record_audit
from app.billing.models import Charge, Invoice, InvoiceItem, Payment, Service
from app.coverage.service import calculate_charge_responsibility, get_verified_current_coverage, has_current_unverified_coverage
from app.encounters.models import Encounter


class BillingError(ValueError):
    pass


def _invoice_number(db: Session) -> str:
    sequence = db.scalar(text("nextval('afasync_invoice_seq')"))
    return f"INV-{datetime.now(timezone.utc):%Y%m%d}-{int(sequence):05d}"


def create_charge(db: Session, facility_id: UUID, payload: dict, *, actor_user_id: UUID | None = None, commit: bool = True) -> Charge:
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
    db.flush()
    if commit:
        db.commit()
        db.refresh(charge)
    record_audit(db, action="CREATE_CHARGE", resource_type="CHARGE", resource_id=str(charge.id), result="SUCCESS", user_id=actor_user_id, facility_id=facility_id, patient_id=encounter.patient_id, metadata={"charge_id": charge.charge_id, "amount": str(total)}, commit=commit)
    return charge


def create_invoice(db: Session, facility_id: UUID, encounter_id: UUID, *, actor_user_id: UUID | None = None) -> Invoice:
    encounter = db.get(Encounter, encounter_id)
    if encounter is None:
        raise BillingError("ENCOUNTER_NOT_FOUND")
    if encounter.facility_id != facility_id:
        raise BillingError("FACILITY_ACCESS_DENIED")
    existing = db.scalar(select(Invoice).where(Invoice.encounter_id == encounter.id, Invoice.facility_id == facility_id, Invoice.status != "VOID").limit(1))
    if existing:
        return existing
    if has_current_unverified_coverage(db, encounter.patient_id):
        raise BillingError("COVERAGE_NOT_VERIFIED")
    coverage = get_verified_current_coverage(db, encounter.patient_id)
    charges = list(db.scalars(select(Charge).where(Charge.encounter_id == encounter.id, Charge.facility_id == facility_id, Charge.status == "ACTIVE").order_by(Charge.created_at, Charge.id)))
    if not charges:
        raise BillingError("NO_CHARGES")

    subtotal = Decimal("0")
    payer_total = Decimal("0")
    patient_total = Decimal("0")
    breakdown: list[tuple[Charge, Service, Decimal, Decimal, UUID | None]] = []
    for charge in charges:
        service = db.get(Service, charge.service_id)
        if service is None:
            raise BillingError("SERVICE_NOT_FOUND")
        amount = Decimal(str(charge.total_amount)).quantize(Decimal("0.01"))
        if coverage is None:
            payer_amount, patient_amount, rule_id = Decimal("0"), amount, None
        else:
            try:
                payer_amount, patient_amount, rule_id = calculate_charge_responsibility(
                    db, coverage, amount=amount, service_code=service.code, service_type=service.service_type
                )
            except ValueError as exc:
                if str(exc) == "COVERAGE_RULE_NOT_CONFIGURED":
                    raise BillingError("COVERAGE_RULE_NOT_CONFIGURED") from exc
                raise
        subtotal += amount
        payer_total += payer_amount
        patient_total += patient_amount
        breakdown.append((charge, service, payer_amount, patient_amount, rule_id))

    invoice = Invoice(
        invoice_id=_invoice_number(db),
        patient_id=encounter.patient_id,
        facility_id=facility_id,
        encounter_id=encounter.id,
        subtotal=subtotal,
        payer_amount=payer_total,
        patient_amount=patient_total,
        total_amount=subtotal,
    )
    db.add(invoice)
    db.flush()
    for charge, service, payer_amount, patient_amount, rule_id in breakdown:
        db.add(
            InvoiceItem(
                invoice_id=invoice.id,
                charge_id=charge.id,
                description=f"{service.code} - {service.name}",
                quantity=charge.quantity,
                unit_price=charge.unit_price,
                amount=charge.total_amount,
                payer_amount=payer_amount,
                patient_amount=patient_amount,
                benefit_rule_id=rule_id,
            )
        )
    db.commit()
    db.refresh(invoice)
    record_audit(
        db,
        action="CREATE_INVOICE",
        resource_type="INVOICE",
        resource_id=str(invoice.id),
        result="SUCCESS",
        user_id=actor_user_id,
        facility_id=facility_id,
        patient_id=invoice.patient_id,
        metadata={
            "invoice_id": invoice.invoice_id,
            "amount": str(invoice.total_amount),
            "payer_amount": str(invoice.payer_amount),
            "patient_amount": str(invoice.patient_amount),
            "coverage_id": str(coverage.id) if coverage else None,
        },
    )
    return invoice


def record_payment(db: Session, facility_id: UUID, payload: dict, *, actor_user_id: UUID | None = None) -> Payment:
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
    if paid + amount > Decimal(str(invoice.patient_amount)):
        raise BillingError("PAYMENT_EXCEEDS_BALANCE")
    payment = Payment(transaction_id=transaction_id, invoice_id=invoice.id, patient_id=invoice.patient_id, facility_id=facility_id, amount=amount, payment_method=payload["payment_method"], provider=payload.get("provider"), external_reference=payload.get("external_reference"), status="CONFIRMED", confirmed_at=datetime.now(timezone.utc))
    db.add(payment)
    db.flush()
    new_paid = paid + amount
    invoice.status = "PAID" if new_paid == Decimal(str(invoice.patient_amount)) else "PARTIALLY_PAID"
    db.commit()
    db.refresh(payment)
    record_audit(db, action="RECORD_PAYMENT", resource_type="PAYMENT", resource_id=str(payment.id), result="SUCCESS", user_id=actor_user_id, facility_id=facility_id, patient_id=payment.patient_id, metadata={"transaction_id": payment.transaction_id, "amount": str(amount), "invoice_id": str(invoice.id)})
    return payment
