from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit.service import record_audit
from app.billing.models import Charge, Invoice, InvoiceItem, Service
from app.claims.models import Claim
from app.claims.service import ClaimsError, _contract_operational_gate
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
    invoice = db.scalar(
        select(Invoice).where(
            Invoice.id == invoice_id,
            Invoice.facility_id == facility_id,
        )
    )
    if invoice is None:
        raise ClaimsError("INVOICE_NOT_FOUND")

    errors: list[str] = []
    warnings: list[str] = []
    benefit_summary: dict | None = None
    today = date.today()
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

    enrolled = db.scalar(
        select(PatientFacility.id).where(
            PatientFacility.patient_id == invoice.patient_id,
            PatientFacility.facility_id == facility_id,
            PatientFacility.status == "ACTIVE",
        )
    )
    if enrolled is None:
        errors.append("PATIENT_NOT_IN_FACILITY")

    coverage = db.get(Coverage, coverage_id) if coverage_id else None
    if coverage is None:
        if coverage_id is not None:
            errors.append("COVERAGE_NOT_FOUND")
    else:
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

    existing_claim = db.scalar(
        select(Claim.id).where(Claim.invoice_id == invoice.id).limit(1)
    )
    if existing_claim is not None:
        errors.append("CLAIM_ALREADY_EXISTS")

    items = list(
        db.scalars(select(InvoiceItem).where(InvoiceItem.invoice_id == invoice.id)).all()
    )
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
        if (
            charge.facility_id != facility_id
            or charge.encounter_id != invoice.encounter_id
            or charge.patient_id != invoice.patient_id
        ):
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

    # Phase 104/106 — benefit engine + preauth gate
    if payer_id is not None and items and "PAYER_COVERAGE_REQUIRED" not in errors:
        try:
            from app.benefit_engine.service import quote_lines

            lines = []
            for item in items:
                charge = db.get(Charge, item.charge_id)
                service = db.get(Service, charge.service_id) if charge else None
                if not service:
                    continue
                lines.append(
                    {
                        "line_id": str(item.id),
                        "service_code": service.code,
                        "service_type": getattr(service, "service_type", None),
                        "gross_amount": float(item.amount),
                    }
                )
            if lines:
                plan_id = getattr(coverage, "payer_plan_id", None) if coverage is not None else None
                benefit_summary = quote_lines(
                    db,
                    payer_id=payer_id,
                    payer_plan_id=plan_id,
                    package_id=None,
                    as_of=today,
                    lines=lines,
                )
                for line in benefit_summary.get("lines") or []:
                    code = line.get("service_code") or line.get("line_id") or "LINE"
                    decision = line.get("decision")
                    reason = line.get("reason_code")
                    if decision == "INELIGIBLE":
                        errors.append(f"BENEFIT_EXCLUDED:{code}")
                    elif decision == "UNKNOWN" or reason == "NO_ACTIVE_BENEFIT_RULE":
                        warnings.append(f"BENEFIT_RULE_MISSING:{code}")
                    elif decision == "CONDITIONAL" or line.get("requires_preauth"):
                        warnings.append(f"BENEFIT_PREAUTH_REQUIRED:{code}")
                        try:
                            from app.financing_preauthorization.service import find_active_authorization

                            auth = find_active_authorization(
                                db,
                                facility_id=facility_id,
                                person_id=invoice.patient_id,
                                payer_id=payer_id,
                                service_code=code if code != "LINE" else None,
                            )
                            if auth is None:
                                errors.append(f"PREAUTH_REQUIRED:{code}")
                            else:
                                warnings.append(
                                    f"PREAUTH_OK:{code}:{auth.authorization_number}:{auth.status}"
                                )
                        except Exception:
                            errors.append(f"PREAUTH_REQUIRED:{code}")
                engine_payer = Decimal(str(benefit_summary.get("payer_total") or 0)).quantize(Decimal("0.01"))
                if payer_total > 0 and engine_payer >= 0:
                    delta = abs(payer_total - engine_payer)
                    if delta > Decimal("50.00") and (delta / payer_total) > Decimal("0.05"):
                        warnings.append(
                            f"BENEFIT_AMOUNT_VARIANCE:invoice_payer={payer_total},engine_payer={engine_payer}"
                        )
        except Exception:
            warnings.append("BENEFIT_ENGINE_UNAVAILABLE")

    if payer is not None and not errors:
        try:
            gate_codes = []
            gate_amounts = []
            gate_quantities = []
            for item in items:
                charge = db.get(Charge, item.charge_id)
                service = db.get(Service, charge.service_id) if charge else None
                if service:
                    gate_codes.append(service.code)
                    gate_amounts.append(Decimal(str(item.payer_amount)))
                    gate_quantities.append(Decimal(str(charge.quantity)))
            _contract_operational_gate(db, facility_id, payer, gate_codes, gate_amounts, gate_quantities)
        except ClaimsError as exc:
            errors.append(str(exc))

    deduped_errors = list(dict.fromkeys(errors))
    deduped_warnings = list(dict.fromkeys(warnings))

    from app.claims.risk_service import score_from_preflight

    risk = score_from_preflight(
        errors=deduped_errors,
        warnings=deduped_warnings,
        payer_amount=float(payer_total),
    )

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
            "risk_score": risk.score,
            "risk_band": risk.band,
            "block_submit": risk.block_submit,
            "benefit_unknown_rules": (benefit_summary or {}).get("unknown_rules"),
            "benefit_preauth_lines": (benefit_summary or {}).get("preauth_required_lines"),
            "benefit_ineligible_lines": (benefit_summary or {}).get("ineligible_lines"),
            "benefit_engine_payer_total": (benefit_summary or {}).get("payer_total"),
        },
        commit=True,
    )
    from app.claims.preflight_schemas import ClaimPreflightResponse, RiskFactorOut

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
        risk_score=risk.score,
        risk_band=risk.band,
        block_submit=risk.block_submit,
        risk_factors=[
            RiskFactorOut(
                code=f.code,
                severity=f.severity,
                points=f.points,
                message=f.message,
                owner=f.owner,
            )
            for f in risk.factors
        ],
        benefit_unknown_rules=int((benefit_summary or {}).get("unknown_rules") or 0),
        benefit_preauth_lines=int((benefit_summary or {}).get("preauth_required_lines") or 0),
        benefit_ineligible_lines=int((benefit_summary or {}).get("ineligible_lines") or 0),
        benefit_engine_payer_total=float((benefit_summary or {}).get("payer_total") or 0),
        benefit_engine_patient_total=float((benefit_summary or {}).get("patient_total") or 0),
    )
