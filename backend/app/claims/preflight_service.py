from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit.service import record_audit
from app.billing.models import Charge, Invoice, InvoiceItem, Service
from app.claims.models import Claim
from app.claims.service import ClaimsError
from app.coverage.models import Coverage, Payer
from app.encounters.models import Encounter
from app.patients.models import PatientFacility


def preflight_claim(
    db: Session,
    *,
    invoice_id: UUID,
    facility_id: UUID,
    actor_user_id: UUID,
):
    invoice = db.scalar(select(Invoice).where(Invoice.id == invoice_id))
    if invoice is None:
        raise ClaimsError("INVOICE_NOT_FOUND")
    if invoice.facility_id != facility_id:
        raise ClaimsError("FACILITY_ACCESS_DENIED")

    errors: list[str] = []
    warnings: list[str] = []
    payer_id = invoice.payer_id
    coverage_id = invoice.coverage_id

    if invoice.status == "VOID":
        errors.append("INVOICE_VOID")
    if payer_id is None or coverage_id is None:
        errors.append("PAYER_COVERAGE_REQUIRED")

    encounter = db.get(Encounter, invoice.encounter_id)
    if encounter is None:
        errors.append("ENCOUNTER_NOT_FOUND")
    elif encounter.facility_id != facility_id or encounter.patient_id != invoice.patient_id:
        errors.append("ENCOUNTER_MISMATCH")
    elif (getattr(encounter, "coverage_mode", None) or "CASH") == "CASH":
        errors.append("CASH_ENCOUNTER_NO_CLAIM")

    enrolled = db.scalar(select(PatientFacility.id).where(
        PatientFacility.patient_id == invoice.patient_id,
        PatientFacility.facility_id == facility_id,
        PatientFacility.status == "ACTIVE",
    ))
    if enrolled is None:
        errors.append("PATIENT_NOT_IN_FACILITY")

    coverage = db.get(Coverage, coverage_id) if coverage_id else None
    if coverage is None:
        if coverage_id is not None:
            errors.append("COVERAGE_NOT_FOUND")
    else:
        today = date.today()
        if coverage.person_id != invoice.patient_id or coverage.payer_id != payer_id:
            errors.append("COVERAGE_INVOICE_MISMATCH")
        if coverage.status != "ACTIVE" or coverage.verification_status != "VERIFIED":
            errors.append("VERIFIED_COVERAGE_REQUIRED")
        if coverage.start_date and today < coverage.start_date:
            errors.append("COVERAGE_NOT_YET_ACTIVE")
        if coverage.end_date and today > coverage.end_date:
            errors.append("COVERAGE_EXPIRED")

    payer = db.get(Payer, payer_id) if payer_id else None
    if payer is None:
        if payer_id is not None:
            errors.append("PAYER_NOT_FOUND")
    elif payer.status != "ACTIVE":
        errors.append("PAYER_NOT_ACTIVE")

    existing_claim = db.scalar(select(Claim.id).where(Claim.invoice_id == invoice.id).limit(1))
    if existing_claim is not None:
        errors.append("CLAIM_ALREADY_EXISTS")

    items = list(db.scalars(select(InvoiceItem).where(InvoiceItem.invoice_id == invoice.id)).all())
    if not items:
        errors.append("CLAIM_ITEMS_REQUIRED")

    payer_total = Decimal("0.00")
    patient_total = Decimal("0.00")
    for item in items:
        amount = Decimal(str(item.amount)).quantize(Decimal("0.01"))
        payer_amount = Decimal(str(item.payer_amount)).quantize(Decimal("0.01"))
        patient_amount = Decimal(str(item.patient_amount)).quantize(Decimal("0.01"))
        if amount < 0 or payer_amount < 0 or patient_amount < 0:
            errors.append("NEGATIVE_INVOICE_ITEM_AMOUNT")
            continue
        if payer_amount + patient_amount != amount:
            errors.append("INVOICE_ITEM_RESPONSIBILITY_MISMATCH")
        charge = db.get(Charge, item.charge_id)
        if charge is None:
            errors.append("CHARGE_NOT_FOUND")
            continue
        if charge.facility_id != facility_id or charge.encounter_id != invoice.encounter_id or charge.patient_id != invoice.patient_id:
            errors.append("CHARGE_SCOPE_MISMATCH")
            continue
        service = db.get(Service, charge.service_id)
        if service is None or service.facility_id != facility_id:
            errors.append("SERVICE_NOT_FOUND")
        payer_total += payer_amount
        patient_total += patient_amount

    invoice_payer = Decimal(str(invoice.payer_amount)).quantize(Decimal("0.01"))
    invoice_patient = Decimal(str(invoice.patient_amount)).quantize(Decimal("0.01"))
    invoice_total = Decimal(str(invoice.total_amount)).quantize(Decimal("0.01"))
    subtotal = Decimal(str(invoice.subtotal)).quantize(Decimal("0.01"))
    if payer_total != invoice_payer:
        errors.append("CLAIM_INVOICE_TOTAL_MISMATCH")
    if patient_total != invoice_patient:
        errors.append("INVOICE_PATIENT_TOTAL_MISMATCH")
    if invoice_payer + invoice_patient != invoice_total or invoice_total != subtotal:
        errors.append("INVOICE_TOTAL_INTEGRITY_ERROR")

    if payer is not None and payer.integration_status != "CONFIGURED":
        warnings.append("PAYER_INTEGRATION_NOT_CONFIGURED")

    deduped_errors = list(dict.fromkeys(errors))
    deduped_warnings = list(dict.fromkeys(warnings))
    record_audit(
        db,
        action="CLAIM_PREFLIGHT",
        resource_type="INVOICE",
        resource_id=str(invoice.id),
        result="READY" if not deduped_errors else "NOT_READY",
        user_id=actor_user_id,
        facility_id=facility_id,
        patient_id=invoice.patient_id,
        metadata={
            "error_count": len(deduped_errors),
            "warning_count": len(deduped_warnings),
            "item_count": len(items),
            "payer_amount": str(payer_total),
            "patient_amount": str(patient_total),
        },
        commit=True,
    )
    from app.claims.preflight_schemas import ClaimPreflightResponse
    return ClaimPreflightResponse(
        invoice_id=invoice.id,
        ready=not deduped_errors,
        errors=deduped_errors,
        warnings=deduped_warnings,
        payer_id=payer_id,
        coverage_id=coverage_id,
        payer_amount=float(payer_total),
        patient_amount=float(patient_total),
        item_count=len(items),
    )
