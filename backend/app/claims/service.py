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
from app.integrations.models import Integration, IntegrationTransaction
from app.integrations.service import IntegrationError, queue_transaction
from app.notifications.events import notify_patient_event


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
    invoice = db.scalar(select(Invoice).where(Invoice.id == invoice_id).with_for_update())
    if invoice is None: raise ClaimsError("INVOICE_NOT_FOUND")
    if invoice.facility_id != facility_id: raise ClaimsError("FACILITY_ACCESS_DENIED")
    if invoice.status == "VOID": raise ClaimsError("INVOICE_VOID")
    if invoice.payer_id is None or invoice.coverage_id is None: raise ClaimsError("PAYER_COVERAGE_REQUIRED")
    encounter = db.get(Encounter, invoice.encounter_id)
    if encounter is None or encounter.facility_id != facility_id or encounter.patient_id != invoice.patient_id: raise ClaimsError("ENCOUNTER_MISMATCH")
    mode = getattr(encounter, "coverage_mode", None) or "CASH"
    if mode == "CASH": raise ClaimsError("CASH_ENCOUNTER_NO_CLAIM")
    existing = db.scalar(select(Claim).where(Claim.invoice_id == invoice.id).limit(1))
    if existing: raise ClaimsError("CLAIM_ALREADY_EXISTS")
    coverage = db.get(Coverage, invoice.coverage_id)
    if coverage is None or coverage.person_id != invoice.patient_id or coverage.payer_id != invoice.payer_id or coverage.status != "ACTIVE" or coverage.verification_status != "VERIFIED" or (coverage.start_date and coverage.start_date > date.today()) or (coverage.end_date and coverage.end_date < date.today()): raise ClaimsError("VERIFIED_COVERAGE_REQUIRED")
    payer = db.get(Payer, invoice.payer_id)
    if payer is None or payer.status != "ACTIVE": raise ClaimsError("PAYER_NOT_ACTIVE")
    payer_code = (payer.code or "").upper()
    if mode == "SHA" and payer_code not in {"SHA", "SHIF", "PHF", "ECCIF"}: raise ClaimsError("SHA_MODE_REQUIRES_SHA_PAYER")
    if mode == "AFYASYNC" and payer_code != "AFYASYNC": raise ClaimsError("AFYASYNC_MODE_REQUIRES_AFYASYNC_PAYER")
    items = list(db.scalars(select(InvoiceItem).where(InvoiceItem.invoice_id == invoice.id)))
    if not items: raise ClaimsError("CLAIM_ITEMS_REQUIRED")
    claim = Claim(claim_id=_claim_number(), invoice_id=invoice.id, encounter_id=encounter.id, patient_id=invoice.patient_id, payer_id=payer.id, claim_amount=Decimal("0"))
    db.add(claim); db.flush()
    claim_amount = Decimal("0")
    for item in items:
        payer_amount = Decimal(str(item.payer_amount)).quantize(Decimal("0.01"))
        if payer_amount <= 0: continue
        charge = db.get(Charge, item.charge_id)
        if charge is None or charge.facility_id != facility_id or charge.encounter_id != encounter.id or charge.patient_id != invoice.patient_id: raise ClaimsError("CHARGE_NOT_FOUND")
        service = db.get(Service, charge.service_id)
        if service is None or service.facility_id != facility_id: raise ClaimsError("SERVICE_NOT_FOUND")
        db.add(ClaimItem(claim_id=claim.id, charge_id=charge.id, service_code=service.code, quantity=charge.quantity, amount=payer_amount)); claim_amount += payer_amount
    if claim_amount <= 0: raise ClaimsError("CLAIM_AMOUNT_INVALID")
    if claim_amount != Decimal(str(invoice.payer_amount)).quantize(Decimal("0.01")): raise ClaimsError("CLAIM_INVOICE_TOTAL_MISMATCH")
    claim.claim_amount = claim_amount; invoice.status = "CLAIM_PENDING"; db.flush()
    record_audit(db, action="CREATE_CLAIM", resource_type="CLAIM", resource_id=str(claim.id), result="SUCCESS", user_id=actor_user_id, facility_id=facility_id, patient_id=claim.patient_id, metadata={"claim_id": claim.claim_id, "amount": str(claim.claim_amount), "payer_id": str(payer.id), "coverage_mode": mode, "payer_code": payer_code}, commit=False)
    db.commit(); db.refresh(claim); return claim


def validate_claim(db: Session, claim_id: UUID, facility_id: UUID, *, actor_user_id: UUID | None = None) -> list[str]:
    claim = db.scalar(select(Claim).where(Claim.id == claim_id).with_for_update())
    if claim is None: raise ClaimsError("CLAIM_NOT_FOUND")
    invoice = db.get(Invoice, claim.invoice_id)
    if invoice is None or invoice.facility_id != facility_id: raise ClaimsError("FACILITY_ACCESS_DENIED")
    errors: list[str] = []
    if claim.status not in {"DRAFT", "READY", "REJECTED"}: errors.append("CLAIM_NOT_VALIDATABLE")
    if claim.claim_amount <= 0: errors.append("CLAIM_AMOUNT_INVALID")
    items = list(db.scalars(select(ClaimItem).where(ClaimItem.claim_id == claim.id)))
    if not items: errors.append("CLAIM_ITEMS_REQUIRED")
    elif sum((Decimal(str(item.amount)) for item in items), Decimal("0")) != Decimal(str(claim.claim_amount)): errors.append("CLAIM_ITEM_TOTAL_MISMATCH")
    coverage = _verified_current_coverage(db, claim.patient_id, claim.payer_id)
    if coverage is None: errors.append("VERIFIED_COVERAGE_REQUIRED")
    claim.status = "DRAFT" if errors else "READY"; db.flush()
    record_audit(db, action="VALIDATE_CLAIM", resource_type="CLAIM", resource_id=str(claim.id), result="SUCCESS" if not errors else "VALIDATION_FAILED", user_id=actor_user_id, facility_id=facility_id, patient_id=claim.patient_id, metadata={"errors": errors}, commit=False)
    db.commit(); return errors


def _find_payer_submission_integration(db: Session, facility_id: UUID, payer: Payer) -> Integration | None:
    return db.scalar(select(Integration).where(Integration.facility_id == facility_id, Integration.status == "ACTIVE", Integration.integration_type.in_(["PAYER_CLAIMS", "CLAIMS"]), Integration.provider == payer.code).order_by(Integration.created_at.desc()).limit(1))


def build_claim_submission_payload(db: Session, claim_id: UUID, facility_id: UUID) -> dict:
    claim = db.get(Claim, claim_id)
    if claim is None: raise ClaimsError("CLAIM_NOT_FOUND")
    invoice = db.get(Invoice, claim.invoice_id)
    if invoice is None or invoice.facility_id != facility_id: raise ClaimsError("FACILITY_ACCESS_DENIED")
    payer = db.get(Payer, claim.payer_id)
    if payer is None: raise ClaimsError("PAYER_NOT_FOUND")
    encounter = db.get(Encounter, claim.encounter_id)
    if encounter is None or encounter.facility_id != facility_id or encounter.patient_id != claim.patient_id: raise ClaimsError("ENCOUNTER_MISMATCH")
    items = list(db.scalars(select(ClaimItem).where(ClaimItem.claim_id == claim.id)))
    return {"claim_id": claim.claim_id, "invoice_id": str(invoice.id), "encounter_id": str(encounter.id), "patient_id": str(claim.patient_id), "payer_id": str(payer.id), "payer_code": payer.code, "coverage_mode": getattr(encounter, "coverage_mode", None), "claim_amount": str(claim.claim_amount), "items": [{"service_code": item.service_code, "quantity": str(item.quantity), "amount": str(item.amount), "charge_id": str(item.charge_id)} for item in items]}


def submit_claim(db: Session, claim_id: UUID, facility_id: UUID, *, actor_user_id: UUID | None = None) -> Claim:
    claim = db.scalar(select(Claim).where(Claim.id == claim_id).with_for_update())
    if claim is None: raise ClaimsError("CLAIM_NOT_FOUND")
    invoice = db.get(Invoice, claim.invoice_id)
    if invoice is None or invoice.facility_id != facility_id: raise ClaimsError("FACILITY_ACCESS_DENIED")
    if claim.status == "SUBMITTED": return claim
    if claim.status != "READY": raise ClaimsError("CLAIM_NOT_READY")
    payer = db.get(Payer, claim.payer_id)
    if payer is None or payer.status != "ACTIVE": raise ClaimsError("PAYER_NOT_ACTIVE")
    integration = _find_payer_submission_integration(db, facility_id, payer)
    if integration is None: raise ClaimsError("PAYER_INTEGRATION_NOT_CONFIGURED")
    payload = build_claim_submission_payload(db, claim.id, facility_id)
    transaction_id = f"{claim.claim_id}:{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')}"
    try:
        transaction = queue_transaction(db, facility_id, integration.id, transaction_id, "CLAIM", claim.id, "OUTBOUND", claim.claim_id)
    except IntegrationError as exc:
        db.rollback(); raise ClaimsError(str(exc)) from exc
    transaction.response_data = {"request": payload}
    claim.status = "SUBMITTED"; claim.submitted_at = datetime.now(timezone.utc)
    db.add(ClaimResponse(claim_id=claim.id, status="SUBMITTED", response_message="Queued for authorised payer submission")); db.flush()
    notify_patient_event(db, patient_id=claim.patient_id, facility_id=facility_id, event_type="CLAIM_STATUS_CHANGED", action_url=f"/patient/claims/{claim.id}", metadata={"claim_id": claim.claim_id, "status": "SUBMITTED"}, actor_user_id=actor_user_id, commit=False)
    record_audit(db, action="SUBMIT_CLAIM", resource_type="CLAIM", resource_id=str(claim.id), result="SUCCESS", user_id=actor_user_id, facility_id=facility_id, patient_id=claim.patient_id, metadata={"claim_id": claim.claim_id, "integration_id": str(integration.id), "transaction_id": transaction.transaction_id}, commit=False)
    db.commit(); db.refresh(claim); return claim


def record_payer_response(db: Session, claim_id: UUID, facility_id: UUID, status: str, response_code: str | None, response_message: str | None, external_reference: str | None, approved_amount: Decimal | None, *, actor_user_id: UUID | None = None, commit: bool = True) -> Claim:
    status = status.strip().upper()
    allowed = {"ACCEPTED", "UNDER_REVIEW", "REJECTED", "PARTIALLY_PAID", "PAID"}
    if status not in allowed: raise ClaimsError("INVALID_CLAIM_RESPONSE_STATUS")
    claim = db.scalar(select(Claim).where(Claim.id == claim_id).with_for_update())
    if claim is None: raise ClaimsError("CLAIM_NOT_FOUND")
    invoice = db.get(Invoice, claim.invoice_id)
    if invoice is None or invoice.facility_id != facility_id: raise ClaimsError("FACILITY_ACCESS_DENIED")
    current = claim.status
    valid_previous = {"ACCEPTED": {"SUBMITTED", "UNDER_REVIEW"}, "UNDER_REVIEW": {"SUBMITTED", "UNDER_REVIEW"}, "REJECTED": {"SUBMITTED", "UNDER_REVIEW", "REJECTED"}, "PARTIALLY_PAID": {"ACCEPTED", "UNDER_REVIEW", "PARTIALLY_PAID"}, "PAID": {"ACCEPTED", "PARTIALLY_PAID", "PAID"}}
    if current not in valid_previous[status]: raise ClaimsError("CLAIM_RESPONSE_NOT_ALLOWED")
    if approved_amount is not None:
        approved_amount = Decimal(str(approved_amount)).quantize(Decimal("0.01"))
        if approved_amount < 0 or approved_amount > Decimal(str(claim.claim_amount)).quantize(Decimal("0.01")): raise ClaimsError("INVALID_APPROVED_AMOUNT")
    if status in {"ACCEPTED", "PARTIALLY_PAID", "PAID"} and approved_amount is None: raise ClaimsError("APPROVED_AMOUNT_REQUIRED")
    if status == "REJECTED" and approved_amount not in (None, Decimal("0.00")): raise ClaimsError("REJECTED_AMOUNT_MUST_BE_ZERO")
    if status in {"ACCEPTED", "PAID"} and approved_amount == Decimal("0.00"): raise ClaimsError("INVALID_APPROVED_AMOUNT")
    if external_reference:
        external_reference = external_reference.strip()
        if not external_reference: raise ClaimsError("PAYER_EXTERNAL_REFERENCE_REQUIRED")
        duplicate = db.scalar(select(ClaimResponse.id).where(ClaimResponse.claim_id == claim.id, ClaimResponse.external_reference == external_reference).limit(1))
        if duplicate is not None: raise ClaimsError("DUPLICATE_PAYER_RESPONSE")
    if approved_amount is not None: claim.approved_amount = approved_amount
    claim.status = status
    db.add(ClaimResponse(claim_id=claim.id, status=status, response_code=response_code, response_message=response_message, external_reference=external_reference)); db.flush()
    notify_patient_event(db, patient_id=claim.patient_id, facility_id=facility_id, event_type="CLAIM_STATUS_CHANGED", action_url=f"/patient/claims/{claim.id}", priority="HIGH" if status in {"REJECTED", "PARTIALLY_PAID"} else "NORMAL", metadata={"claim_id": claim.claim_id, "status": status}, actor_user_id=actor_user_id, commit=False)
    record_audit(db, action="RECORD_PAYER_RESPONSE", resource_type="CLAIM", resource_id=str(claim.id), result="SUCCESS", user_id=actor_user_id, facility_id=facility_id, patient_id=claim.patient_id, metadata={"status": status, "external_reference": external_reference}, commit=False)
    if commit: db.commit(); db.refresh(claim)
    return claim


def process_payer_callback(db: Session, facility_id: UUID, integration_id: UUID, claim_id: UUID, status: str, response_code: str | None, response_message: str | None, external_reference: str, approved_amount: Decimal | None, *, actor_user_id: UUID | None = None) -> Claim:
    """Compatibility wrapper for the signed integration callback boundary."""
    from app.claims.integration_callback import process_claim_payer_callback
    result, _duplicate = process_claim_payer_callback(db, facility_id=facility_id, integration_id=integration_id, claim_id=claim_id, status=status, response_code=response_code, response_message=response_message, external_reference=external_reference, approved_amount=approved_amount)
    return result


def reconcile_claim(db: Session, claim_id: UUID, facility_id: UUID, staff_id: UUID, received_amount: Decimal, *, actor_user_id: UUID | None = None) -> Reconciliation:
    claim = db.scalar(select(Claim).where(Claim.id == claim_id).with_for_update())
    if claim is None: raise ClaimsError("CLAIM_NOT_FOUND")
    invoice = db.get(Invoice, claim.invoice_id)
    if invoice is None or invoice.facility_id != facility_id: raise ClaimsError("FACILITY_ACCESS_DENIED")
    if claim.status not in {"ACCEPTED", "PARTIALLY_PAID", "PAID"}: raise ClaimsError("CLAIM_NOT_SETTLEABLE")
    received = Decimal(str(received_amount)).quantize(Decimal("0.01"))
    if received < 0: raise ClaimsError("INVALID_RECEIVED_AMOUNT")
    expected = Decimal(str(claim.approved_amount)).quantize(Decimal("0.01"))
    if expected <= 0: raise ClaimsError("CLAIM_APPROVED_AMOUNT_REQUIRED")
    if received > expected: raise ClaimsError("RECEIVED_AMOUNT_EXCEEDS_EXPECTED")
    existing = db.scalar(select(Reconciliation).where(Reconciliation.claim_id == claim.id).with_for_update())
    if existing: raise ClaimsError("CLAIM_ALREADY_RECONCILED")
    difference = received - expected
    status = "MATCHED" if difference == 0 else "VARIANCE"
    reconciliation = Reconciliation(claim_id=claim.id, expected_amount=expected, received_amount=received, difference=difference, status=status, reconciled_by=staff_id, reconciled_at=datetime.now(timezone.utc))
    db.add(reconciliation)
    claim.paid_amount = received
    if claim.status == "ACCEPTED" and received == expected: claim.status = "PAID"
    db.flush()
    record_audit(db, action="RECONCILE_CLAIM", resource_type="RECONCILIATION", resource_id=str(reconciliation.id), result="SUCCESS", user_id=actor_user_id, facility_id=facility_id, patient_id=claim.patient_id, metadata={"claim_id": claim.claim_id, "expected_amount": str(expected), "received_amount": str(received), "difference": str(difference), "status": status}, commit=False)
    db.commit(); db.refresh(reconciliation); return reconciliation
