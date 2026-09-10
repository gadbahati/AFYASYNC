from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.billing.models import Charge, Invoice, InvoiceItem
from app.claims.models import Claim, ClaimItem, Reconciliation
from app.coverage.models import Coverage, Payer
from app.encounters.models import Encounter


class ClaimsError(ValueError):
    pass


def _claim_number() -> str:
    return f"CLM-{datetime.now(timezone.utc):%Y%m%d}-{uuid4().hex[:8].upper()}"


def create_claim(db: Session, facility_id: UUID, invoice_id: UUID) -> Claim:
    invoice = db.get(Invoice, invoice_id)
    if invoice is None:
        raise ClaimsError("INVOICE_NOT_FOUND")
    if invoice.facility_id != facility_id:
        raise ClaimsError("FACILITY_ACCESS_DENIED")
    encounter = db.get(Encounter, invoice.encounter_id)
    if encounter is None or encounter.facility_id != facility_id:
        raise ClaimsError("ENCOUNTER_NOT_FOUND")
    existing = db.scalar(select(Claim).where(Claim.invoice_id == invoice.id).limit(1))
    if existing:
        raise ClaimsError("CLAIM_ALREADY_EXISTS")
    coverage = db.scalar(select(Coverage).where(Coverage.person_id == invoice.patient_id, Coverage.status == "ACTIVE", Coverage.verification_status == "VERIFIED").order_by(Coverage.created_at.desc()).limit(1))
    if coverage is None:
        raise ClaimsError("VERIFIED_COVERAGE_REQUIRED")
    payer = db.get(Payer, coverage.payer_id)
    if payer is None or payer.status != "ACTIVE":
        raise ClaimsError("PAYER_NOT_ACTIVE")
    claim = Claim(claim_id=_claim_number(), invoice_id=invoice.id, encounter_id=encounter.id, patient_id=invoice.patient_id, payer_id=payer.id, claim_amount=invoice.payer_amount or invoice.total_amount)
    db.add(claim)
    db.flush()
    items = list(db.scalars(select(InvoiceItem).where(InvoiceItem.invoice_id == invoice.id)))
    for item in items:
        charge = db.get(Charge, item.charge_id)
        if charge is None:
            raise ClaimsError("CHARGE_NOT_FOUND")
        db.add(ClaimItem(claim_id=claim.id, charge_id=charge.id, service_code=str(charge.service_id), quantity=charge.quantity, amount=charge.total_amount))
    invoice.status = "CLAIM_PENDING"
    db.commit()
    db.refresh(claim)
    return claim


def validate_claim(db: Session, claim_id: UUID, facility_id: UUID) -> list[str]:
    claim = db.get(Claim, claim_id)
    if claim is None:
        raise ClaimsError("CLAIM_NOT_FOUND")
    invoice = db.get(Invoice, claim.invoice_id)
    if invoice is None or invoice.facility_id != facility_id:
        raise ClaimsError("FACILITY_ACCESS_DENIED")
    errors: list[str] = []
    if claim.claim_amount <= 0:
        errors.append("CLAIM_AMOUNT_INVALID")
    if not list(db.scalars(select(ClaimItem).where(ClaimItem.claim_id == claim.id))):
        errors.append("CLAIM_ITEMS_REQUIRED")
    coverage = db.scalar(select(Coverage).where(Coverage.person_id == claim.patient_id, Coverage.payer_id == claim.payer_id, Coverage.status == "ACTIVE", Coverage.verification_status == "VERIFIED").limit(1))
    if coverage is None:
        errors.append("VERIFIED_COVERAGE_REQUIRED")
    if errors:
        claim.status = "DRAFT"
    else:
        claim.status = "READY"
    db.commit()
    return errors


def submit_claim(db: Session, claim_id: UUID, facility_id: UUID) -> Claim:
    claim = db.get(Claim, claim_id)
    if claim is None:
        raise ClaimsError("CLAIM_NOT_FOUND")
    invoice = db.get(Invoice, claim.invoice_id)
    if invoice is None or invoice.facility_id != facility_id:
        raise ClaimsError("FACILITY_ACCESS_DENIED")
    if claim.status != "READY":
        raise ClaimsError("CLAIM_NOT_READY")
    claim.status = "SUBMITTED"
    claim.submitted_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(claim)
    return claim


def reconcile_claim(db: Session, claim_id: UUID, facility_id: UUID, staff_id: UUID, received_amount: Decimal) -> Reconciliation:
    claim = db.get(Claim, claim_id)
    if claim is None:
        raise ClaimsError("CLAIM_NOT_FOUND")
    invoice = db.get(Invoice, claim.invoice_id)
    if invoice is None or invoice.facility_id != facility_id:
        raise ClaimsError("FACILITY_ACCESS_DENIED")
    existing = db.scalar(select(Reconciliation).where(Reconciliation.claim_id == claim.id))
    if existing:
        raise ClaimsError("CLAIM_ALREADY_RECONCILED")
    if received_amount < 0:
        raise ClaimsError("INVALID_RECEIVED_AMOUNT")
    expected = claim.approved_amount if claim.approved_amount > 0 else claim.claim_amount
    difference = received_amount - expected
    status = "MATCHED" if difference == 0 else "PARTIAL" if difference < 0 else "OVERPAID"
    reconciliation = Reconciliation(claim_id=claim.id, expected_amount=expected, received_amount=received_amount, difference=difference, status=status, reconciled_by=staff_id, reconciled_at=datetime.now(timezone.utc))
    claim.paid_amount = received_amount
    claim.status = "PAID" if received_amount >= expected else "PARTIALLY_PAID"
    db.add(reconciliation)
    db.commit()
    db.refresh(reconciliation)
    return reconciliation
