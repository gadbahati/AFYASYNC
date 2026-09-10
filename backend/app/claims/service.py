from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit.service import record_audit
from app.billing.models import Charge, Invoice, InvoiceItem, Service
from app.claims.models import Claim, ClaimItem, ClaimResponse, Reconciliation
from app.coverage.models import Coverage, Payer
from app.encounters.models import Encounter


class ClaimsError(ValueError):
    pass


def _claim_number() -> str:
    return f"CLM-{datetime.now(timezone.utc):%Y%m%d}-{uuid4().hex[:8].upper()}"


def _verified_current_coverage(db: Session, patient_id: UUID, payer_id: UUID | None = None) -> Coverage | None:
    today = date.today()
    filters = [Coverage.person_id == patient_id, Coverage.status == "ACTIVE", Coverage.verification_status == "VERIFIED", (Coverage.start_date.is_(None) | (Coverage.start_date <= today)), (Coverage.end_date.is_(None) | (Coverage.end_date >= today))]
    if payer_id is not None:
        filters.append(Coverage.payer_id == payer_id)
    return db.scalar(select(Coverage).where(*filters).order_by(Coverage.created_at.desc()).limit(1))


def create_claim(db: Session, facility_id: UUID, invoice_id: UUID, *, actor_user_id: UUID | None = None) -> Claim:
    invoice = db.get(Invoice, invoice_id)
    if invoice is None:
        raise ClaimsError("INVOICE_NOT_FOUND")
    if invoice.facility_id != facility_id:
        raise ClaimsError("FACILITY_ACCESS_DENIED")
    if invoice.status == "VOID":
        raise ClaimsError("INVOICE_VOID")
    if invoice.payer_id is None or invoice.coverage_id is None:
        raise ClaimsError("PAYER_COVERAGE_REQUIRED")
    encounter = db.get(Encounter, invoice.encounter_id)
    if encounter is None or encounter.facility_id != facility_id or encounter.patient_id != invoice.patient_id:
        raise ClaimsError("ENCOUNTER_MISMATCH")
    existing = db.scalar(select(Claim).where(Claim.invoice_id == invoice.id).limit(1))
    if existing:
        raise ClaimsError("CLAIM_ALREADY_EXISTS")
    coverage = db.get(Coverage, invoice.coverage_id)
    if coverage is None or coverage.person_id != invoice.patient_id or coverage.payer_id != invoice.payer_id or coverage.status != "ACTIVE" or coverage.verification_status != "VERIFIED" or (coverage.start_date and coverage.start_date > date.today()) or (coverage.end_date and coverage.end_date < date.today()):
        raise ClaimsError("VERIFIED_COVERAGE_REQUIRED")
    payer = db.get(Payer, invoice.payer_id)
    if payer is None or payer.status != "ACTIVE":
        raise ClaimsError("PAYER_NOT_ACTIVE")
    items = list(db.scalars(select(InvoiceItem).where(InvoiceItem.invoice_id == invoice.id)))
    if not items:
        raise ClaimsError("CLAIM_ITEMS_REQUIRED")
    claim = Claim(claim_id=_claim_number(), invoice_id=invoice.id, encounter_id=encounter.id, patient_id=invoice.patient_id, payer_id=payer.id, claim_amount=Decimal("0"))
    db.add(claim)
    db.flush()
    claim_amount = Decimal("0")
    for item in items:
        payer_amount = Decimal(str(item.payer_amount)).quantize(Decimal("0.01"))
        if payer_amount <= 0:
            continue
        charge = db.get(Charge, item.charge_id)
        if charge is None or charge.facility_id != facility_id or charge.encounter_id != encounter.id or charge.patient_id != invoice.patient_id:
            raise ClaimsError("CHARGE_NOT_FOUND")
        service = db.get(Service, charge.service_id)
        if service is None or service.facility_id != facility_id:
            raise ClaimsError("SERVICE_NOT_FOUND")
        db.add(ClaimItem(claim_id=claim.id, charge_id=charge.id, service_code=service.code, quantity=charge.quantity, amount=payer_amount))
        claim_amount += payer_amount
    if claim_amount <= 0:
        raise ClaimsError("CLAIM_AMOUNT_INVALID")
    if claim_amount != Decimal(str(invoice.payer_amount)).quantize(Decimal("0.01")):
        raise ClaimsError("CLAIM_INVOICE_TOTAL_MISMATCH")
    claim.claim_amount = claim_amount
    invoice.status = "CLAIM_PENDING"
    db.commit()
    db.refresh(claim)
    record_audit(db, action="CREATE_CLAIM", resource_type="CLAIM", resource_id=str(claim.id), result="SUCCESS", user_id=actor_user_id, facility_id=facility_id, patient_id=claim.patient_id, metadata={"claim_id": claim.claim_id, "amount": str(claim.claim_amount), "payer_id": str(payer.id)})
    return claim


def validate_claim(db: Session, claim_id: UUID, facility_id: UUID, *, actor_user_id: UUID | None = None) -> list[str]:
    claim = db.get(Claim, claim_id)
    if claim is None:
        raise ClaimsError("CLAIM_NOT_FOUND")
    invoice = db.get(Invoice, claim.invoice_id)
    if invoice is None or invoice.facility_id != facility_id:
        raise ClaimsError("FACILITY_ACCESS_DENIED")
    errors: list[str] = []
    if claim.status not in {"DRAFT", "READY", "REJECTED"}:
        errors.append("CLAIM_NOT_VALIDATABLE")
    if claim.claim_amount <= 0:
        errors.append("CLAIM_AMOUNT_INVALID")
    items = list(db.scalars(select(ClaimItem).where(ClaimItem.claim_id == claim.id)))
    if not items:
        errors.append("CLAIM_ITEMS_REQUIRED")
    elif sum((Decimal(str(item.amount)) for item in items), Decimal("0")) != Decimal(str(claim.claim_amount)):
        errors.append("CLAIM_ITEM_TOTAL_MISMATCH")
    coverage = _verified_current_coverage(db, claim.patient_id, claim.payer_id)
    if coverage is None:
        errors.append("VERIFIED_COVERAGE_REQUIRED")
    claim.status = "DRAFT" if errors else "READY"
    db.commit()
    record_audit(db, action="VALIDATE_CLAIM", resource_type="CLAIM", resource_id=str(claim.id), result="SUCCESS" if not errors else "VALIDATION_FAILED", user_id=actor_user_id, facility_id=facility_id, patient_id=claim.patient_id, metadata={"errors": errors})
    return errors


def submit_claim(db: Session, claim_id: UUID, facility_id: UUID, *, actor_user_id: UUID | None = None) -> Claim:
    claim = db.get(Claim, claim_id)
    if claim is None:
        raise ClaimsError("CLAIM_NOT_FOUND")
    invoice = db.get(Invoice, claim.invoice_id)
    if invoice is None or invoice.facility_id != facility_id:
        raise ClaimsError("FACILITY_ACCESS_DENIED")
    if claim.status == "SUBMITTED":
        return claim
    if claim.status != "READY":
        raise ClaimsError("CLAIM_NOT_READY")
    claim.status = "SUBMITTED"
    claim.submitted_at = datetime.now(timezone.utc)
    db.add(ClaimResponse(claim_id=claim.id, status="SUBMITTED", response_message="Queued for authorised payer submission"))
    db.commit()
    db.refresh(claim)
    record_audit(db, action="SUBMIT_CLAIM", resource_type="CLAIM", resource_id=str(claim.id), result="SUCCESS", user_id=actor_user_id, facility_id=facility_id, patient_id=claim.patient_id, metadata={"claim_id": claim.claim_id})
    return claim


def record_payer_response(db: Session, claim_id: UUID, facility_id: UUID, status: str, response_code: str | None, response_message: str | None, external_reference: str | None, approved_amount: Decimal | None, *, actor_user_id: UUID | None = None) -> Claim:
    allowed = {"ACCEPTED", "UNDER_REVIEW", "REJECTED", "PARTIALLY_PAID", "PAID"}
    if status not in allowed:
        raise ClaimsError("INVALID_CLAIM_RESPONSE_STATUS")
    claim = db.get(Claim, claim_id)
    if claim is None:
        raise ClaimsError("CLAIM_NOT_FOUND")
    invoice = db.get(Invoice, claim.invoice_id)
    if invoice is None or invoice.facility_id != facility_id:
        raise ClaimsError("FACILITY_ACCESS_DENIED")
    current = claim.status
    valid_previous = {
        "ACCEPTED": {"SUBMITTED", "UNDER_REVIEW"},
        "UNDER_REVIEW": {"SUBMITTED", "UNDER_REVIEW"},
        "REJECTED": {"SUBMITTED", "UNDER_REVIEW", "REJECTED"},
        "PARTIALLY_PAID": {"ACCEPTED", "UNDER_REVIEW", "PARTIALLY_PAID"},
        "PAID": {"ACCEPTED", "PARTIALLY_PAID", "PAID"},
    }
    if current not in valid_previous.get(status, set()):
        raise ClaimsError("CLAIM_RESPONSE_NOT_ALLOWED")
    if approved_amount is not None and (approved_amount < 0 or approved_amount > claim.claim_amount):
        raise ClaimsError("INVALID_APPROVED_AMOUNT")
    if status in {"ACCEPTED", "PARTIALLY_PAID", "PAID"} and approved_amount is None:
        raise ClaimsError("APPROVED_AMOUNT_REQUIRED")
    if status == "PAID" and approved_amount == 0:
        raise ClaimsError("INVALID_APPROVED_AMOUNT")
    if external_reference:
        duplicate = db.scalar(select(ClaimResponse.id).where(ClaimResponse.claim_id == claim.id, ClaimResponse.external_reference == external_reference).limit(1))
        if duplicate is not None:
            raise ClaimsError("DUPLICATE_PAYER_RESPONSE")
    if approved_amount is not None:
        claim.approved_amount = approved_amount
    claim.status = status
    db.add(ClaimResponse(claim_id=claim.id, status=status, response_code=response_code, response_message=response_message, external_reference=external_reference))
    db.commit()
    db.refresh(claim)
    record_audit(db, action="RECORD_PAYER_RESPONSE", resource_type="CLAIM", resource_id=str(claim.id), result="SUCCESS", user_id=actor_user_id, facility_id=facility_id, patient_id=claim.patient_id, metadata={"status": status, "external_reference": external_reference})
    return claim


def reconcile_claim(db: Session, claim_id: UUID, facility_id: UUID, staff_id: UUID, received_amount: Decimal, *, actor_user_id: UUID | None = None) -> Reconciliation:
    claim = db.get(Claim, claim_id)
    if claim is None:
        raise ClaimsError("CLAIM_NOT_FOUND")
    invoice = db.get(Invoice, claim.invoice_id)
    if invoice is None or invoice.facility_id != facility_id:
        raise ClaimsError("FACILITY_ACCESS_DENIED")
    if claim.status not in {"ACCEPTED", "PARTIALLY_PAID", "PAID"}:
        raise ClaimsError("CLAIM_NOT_RECONCILABLE")
    existing = db.scalar(select(Reconciliation).where(Reconciliation.claim_id == claim.id))
    if existing:
        raise ClaimsError("CLAIM_ALREADY_RECONCILED")
    if received_amount < 0:
        raise ClaimsError("INVALID_RECEIVED_AMOUNT")
    expected = claim.approved_amount if claim.approved_amount > 0 else claim.claim_amount
    if received_amount > expected:
        raise ClaimsError("RECEIVED_AMOUNT_EXCEEDS_EXPECTED")
    difference = received_amount - expected
    status = "MATCHED" if difference == 0 else "PARTIAL"
    reconciliation = Reconciliation(claim_id=claim.id, expected_amount=expected, received_amount=received_amount, difference=difference, status=status, reconciled_by=staff_id, reconciled_at=datetime.now(timezone.utc))
    claim.paid_amount = received_amount
    claim.status = "PAID" if received_amount == expected else "PARTIALLY_PAID"
    db.add(reconciliation)
    db.commit()
    db.refresh(reconciliation)
    record_audit(db, action="RECONCILE_CLAIM", resource_type="RECONCILIATION", resource_id=str(reconciliation.id), result="SUCCESS", user_id=actor_user_id, facility_id=facility_id, patient_id=claim.patient_id, metadata={"claim_id": claim.claim_id, "expected": str(expected), "received": str(received_amount), "difference": str(difference), "status": status})
    return reconciliation
