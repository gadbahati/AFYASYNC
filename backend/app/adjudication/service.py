from datetime import date
from decimal import Decimal
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.audit.service import record_audit
from app.claims.models import Claim, ClaimItem
from app.coverage.models import Coverage, PayerBenefitRule
from app.financing_preauthorization.models import FinancingPreauthorization
from app.adjudication.models import ClaimAdjudication, ClaimLineAdjudication

class AdjudicationError(ValueError):
    pass

def adjudicate(db: Session, *, claim_id, facility_id, actor_user_id, force=False):
    claim = db.scalar(select(Claim).where(Claim.id == claim_id).with_for_update())
    if claim is None:
        raise AdjudicationError("CLAIM_NOT_FOUND")
    from app.billing.models import Invoice
    invoice = db.get(Invoice, claim.invoice_id)
    if invoice is None or invoice.facility_id != facility_id:
        raise AdjudicationError("FACILITY_ACCESS_DENIED")
    if claim.status not in {"DRAFT","READY","SUBMITTED","UNDER_REVIEW","REJECTED"}:
        raise AdjudicationError("CLAIM_NOT_ADJUDICABLE")
    existing = db.scalar(select(ClaimAdjudication).where(ClaimAdjudication.claim_id == claim.id))
    if existing and not force:
        return existing
    if existing and force:
        db.query(ClaimLineAdjudication).filter(ClaimLineAdjudication.adjudication_id == existing.id).delete(synchronize_session=False)
        db.delete(existing)
        db.flush()
    coverage = db.get(Coverage, invoice.coverage_id)
    if coverage is None or coverage.person_id != claim.patient_id or coverage.payer_id != claim.payer_id or coverage.status != "ACTIVE" or coverage.verification_status != "VERIFIED":
        raise AdjudicationError("VERIFIED_COVERAGE_REQUIRED")
    today = date.today()
    if (coverage.start_date and coverage.start_date > today) or (coverage.end_date and coverage.end_date < today):
        raise AdjudicationError("COVERAGE_OUTSIDE_VALID_DATES")
    items = list(db.scalars(select(ClaimItem).where(ClaimItem.claim_id == claim.id)))
    if not items:
        raise AdjudicationError("CLAIM_ITEMS_REQUIRED")
    total = Decimal("0")
    allowed = Decimal("0")
    patient = Decimal("0")
    line_rows = []
    for item in items:
        submitted = Decimal(str(item.amount)).quantize(Decimal("0.01"))
        rule = db.scalar(select(PayerBenefitRule).where(PayerBenefitRule.payer_id == claim.payer_id, PayerBenefitRule.service_code == item.service_code).order_by(PayerBenefitRule.created_at.desc()).limit(1))
        if rule is None:
            line_allowed, decision, reason = Decimal("0"), "DENIED", "NO_BENEFIT_RULE"
        elif getattr(rule, "is_excluded", False):
            line_allowed, decision, reason = Decimal("0"), "DENIED", "SERVICE_EXCLUDED"
        elif getattr(rule, "requires_preauth", False):
            pa = db.scalar(select(FinancingPreauthorization).where(FinancingPreauthorization.person_id == claim.patient_id, FinancingPreauthorization.coverage_id == coverage.id, FinancingPreauthorization.service_code == item.service_code, FinancingPreauthorization.status.in_([ "AUTHORIZED", "CONDITIONAL" ])).order_by(FinancingPreauthorization.decided_at.desc()).limit(1))
            if pa is None:
                line_allowed, decision, reason = Decimal("0"), "DENIED", "PREAUTH_REQUIRED"
            else:
                line_allowed = min(submitted, Decimal(str(pa.approved_amount)))
                decision, reason = ("ALLOWED" if line_allowed == submitted else "PARTIAL"), "PREAUTH_LIMIT"
        else:
            percent = Decimal(str(getattr(rule, "payer_percent", 100) or 0)) / Decimal("100")
            fixed = Decimal(str(getattr(rule, "fixed_patient_copay", 0) or 0))
            cap = getattr(rule, "max_covered_amount", None)
            line_allowed = max(Decimal("0"), (submitted * percent - fixed).quantize(Decimal("0.01")))
            if cap is not None:
                line_allowed = min(line_allowed, Decimal(str(cap)))
            line_allowed = min(submitted, line_allowed)
            decision = "ALLOWED" if line_allowed == submitted else ("PARTIAL" if line_allowed > 0 else "DENIED")
            reason = "BENEFIT_RULE"
        line_patient = submitted - line_allowed
        total += submitted
        allowed += line_allowed
        patient += line_patient
        line_rows.append((item, submitted, line_allowed, decision, reason))
    overall = "APPROVED" if allowed == total else ("PARTIALLY_APPROVED" if allowed > 0 else "DENIED")
    reason = "ALL_LINES_ALLOWED" if overall == "APPROVED" else ("PARTIAL_BENEFIT" if allowed > 0 else "NO_PAYABLE_LINES")
    row = ClaimAdjudication(claim_id=claim.id, decision=overall, submitted_amount=total, allowed_amount=allowed, patient_amount=patient, reason_code=reason, evidence={"engine":"AFYASYNC_ADJUDICATOR_V1","payer_id":str(claim.payer_id),"coverage_id":str(coverage.id),"line_count":len(items)}, adjudicated_by=actor_user_id)
    db.add(row)
    db.flush()
    for item, sub, allow, dec, why in line_rows:
        db.add(ClaimLineAdjudication(adjudication_id=row.id, claim_item_id=item.id, submitted_amount=sub, allowed_amount=allow, decision=dec, reason_code=why, evidence={"service_code":item.service_code}))
    claim.approved_amount = allowed
    claim.status = "REJECTED" if overall == "DENIED" else "ACCEPTED"
    record_audit(db, action="ADJUDICATE_CLAIM", resource_type="CLAIM_ADJUDICATION", resource_id=str(row.id), result=overall, user_id=actor_user_id, facility_id=facility_id, patient_id=claim.patient_id, metadata={"claim_id":claim.claim_id,"submitted":str(total),"allowed":str(allowed),"patient":str(patient),"reason":reason}, commit=False)
    db.commit()
    db.refresh(row)
    return row
