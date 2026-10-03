"""Phase 105 — apply benefit-engine quotes to billing invoices.

Developer: BAHATI GAD WANGWE
"""
from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit.service import record_audit
from app.billing.models import Charge, Invoice, InvoiceItem, Service


def _billing_error(code: str):
    from app.billing.service import BillingError

    raise BillingError(code)


def reprice_invoice_with_benefit_engine(
    db: Session,
    facility_id: UUID,
    invoice_id: UUID,
    *,
    actor_user_id: UUID | None = None,
) -> Invoice:
    invoice = db.scalar(
        select(Invoice).where(Invoice.id == invoice_id, Invoice.facility_id == facility_id)
    )
    if invoice is None:
        _billing_error("INVOICE_NOT_FOUND")
    if invoice.status in {"PAID", "VOID"}:
        _billing_error("INVOICE_NOT_REPRICABLE")
    if invoice.payer_id is None:
        _billing_error("PAYER_REQUIRED_FOR_REPRICE")

    items = list(db.scalars(select(InvoiceItem).where(InvoiceItem.invoice_id == invoice.id)).all())
    if not items:
        _billing_error("CLAIM_ITEMS_REQUIRED")

    from app.benefit_engine.service import quote_lines
    from app.coverage.models import Coverage

    coverage = db.get(Coverage, invoice.coverage_id) if invoice.coverage_id else None
    plan_id = getattr(coverage, "payer_plan_id", None) if coverage is not None else None

    lines = []
    item_by_line: dict[str, InvoiceItem] = {}
    for item in items:
        charge = db.get(Charge, item.charge_id)
        service = db.get(Service, charge.service_id) if charge else None
        if service is None:
            _billing_error("SERVICE_NOT_FOUND")
        lid = str(item.id)
        item_by_line[lid] = item
        lines.append(
            {
                "line_id": lid,
                "service_code": service.code,
                "service_type": getattr(service, "service_type", None),
                "gross_amount": float(item.amount),
            }
        )

    summary = quote_lines(
        db,
        payer_id=invoice.payer_id,
        payer_plan_id=plan_id,
        package_id=None,
        as_of=None,
        lines=lines,
    )

    payer_total = Decimal("0.00")
    patient_total = Decimal("0.00")
    line_results = []
    for line in summary.get("lines") or []:
        item = item_by_line.get(str(line.get("line_id")))
        if item is None:
            continue
        decision = line.get("decision")
        gross = Decimal(str(item.amount)).quantize(Decimal("0.01"))
        if decision in {"INELIGIBLE", "UNKNOWN"}:
            payer_amt = Decimal("0.00")
            patient_amt = gross
        else:
            payer_amt = Decimal(str(line.get("payer_amount") or 0)).quantize(Decimal("0.01"))
            patient_amt = Decimal(str(line.get("patient_amount") or 0)).quantize(Decimal("0.01"))
            if payer_amt + patient_amt != gross:
                patient_amt = (gross - payer_amt).quantize(Decimal("0.01"))
                if patient_amt < 0:
                    patient_amt = Decimal("0.00")
                    payer_amt = gross
        item.payer_amount = float(payer_amt)
        item.patient_amount = float(patient_amt)
        payer_total += payer_amt
        patient_total += patient_amt
        line_results.append(
            {
                "invoice_item_id": str(item.id),
                "decision": decision,
                "reason_code": line.get("reason_code"),
                "payer_amount": float(payer_amt),
                "patient_amount": float(patient_amt),
            }
        )

    invoice.payer_amount = float(payer_total)
    invoice.patient_amount = float(patient_total)

    record_audit(
        db,
        action="REPRICE_INVOICE_BENEFIT_ENGINE",
        resource_type="INVOICE",
        resource_id=str(invoice.id),
        result="SUCCESS",
        user_id=actor_user_id,
        facility_id=facility_id,
        patient_id=invoice.patient_id,
        metadata={
            "invoice_id": invoice.invoice_id,
            "payer_total": str(payer_total),
            "patient_total": str(patient_total),
            "unknown_rules": summary.get("unknown_rules"),
            "preauth_lines": summary.get("preauth_required_lines"),
            "ineligible_lines": summary.get("ineligible_lines"),
            "lines": line_results,
        },
        commit=False,
    )
    db.commit()
    db.refresh(invoice)
    return invoice


def responsibility_from_benefit_engine(
    db: Session,
    *,
    payer_id: UUID,
    payer_plan_id: UUID | None,
    amount: Decimal,
    service_code: str,
    service_type: str,
) -> tuple[Decimal, Decimal, UUID | None]:
    from app.benefit_engine.service import quote

    class _P:
        pass

    payload = _P()
    payload.payer_id = payer_id
    payload.payer_plan_id = payer_plan_id
    payload.benefit_package_id = None
    payload.service_code = service_code
    payload.service_type = service_type
    payload.gross_amount = float(amount)
    payload.as_of = None
    result = quote(db, payload)
    amount = amount.quantize(Decimal("0.01"))
    payer_amount = Decimal(str(result.get("payer_amount") or 0)).quantize(Decimal("0.01"))
    patient_amount = Decimal(str(result.get("patient_amount") or 0)).quantize(Decimal("0.01"))
    if payer_amount + patient_amount != amount:
        patient_amount = (amount - payer_amount).quantize(Decimal("0.01"))
        if patient_amount < 0:
            patient_amount = Decimal("0.00")
            payer_amount = amount
    return payer_amount, patient_amount, result.get("rule_id")
