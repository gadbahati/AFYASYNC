from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.audit.service import record_audit
from app.eligibility.service import evaluate_eligibility
from app.financing_preauthorization.models import FinancingPreauthorization

class FinancingPreauthError(ValueError):
    pass

def request(db: Session, *, facility_id, actor_user_id, payload):
    eligibility = evaluate_eligibility(db, person_id=payload.person_id, service_code=payload.service_code, service_type=payload.service_type, payer_id=payload.payer_id, payer_plan_id=None, gross_amount=payload.requested_amount)
    if eligibility["decision"] == "INELIGIBLE":
        raise FinancingPreauthError(eligibility["reason_code"])
    if eligibility["decision"] == "UNKNOWN":
        raise FinancingPreauthError("ELIGIBILITY_UNKNOWN")
    if eligibility["decision"] != "CONDITIONAL":
        raise FinancingPreauthError("PREAUTH_NOT_REQUIRED")
    row = FinancingPreauthorization(
        authorization_number=f"FXPA-{datetime.now(timezone.utc):%Y%m%d}-{uuid4().hex[:10].upper()}",
        person_id=payload.person_id, facility_id=facility_id, coverage_id=eligibility["coverage_id"],
        payer_id=payload.payer_id, service_code=payload.service_code, service_type=payload.service_type,
        requested_amount=Decimal(str(payload.requested_amount)), status="PENDING",
        decision_reason="PREAUTH_REQUIRED",
        evidence=eligibility.get("evidence") or {},
    )
    db.add(row)
    record_audit(db, action="FINANCING_PREAUTH_REQUESTED", resource_type="FINANCING_PREAUTHORIZATION", resource_id=str(row.id), result="PENDING", user_id=actor_user_id, facility_id=facility_id, patient_id=payload.person_id, metadata={"authorization_number": row.authorization_number, "payer_id": str(payload.payer_id)}, commit=False)
    db.commit(); db.refresh(row)
    return row

def decide(db: Session, *, authorization_id, facility_id, actor_user_id, payload):
    row=db.scalar(select(FinancingPreauthorization).where(FinancingPreauthorization.id==authorization_id, FinancingPreauthorization.facility_id==facility_id).with_for_update())
    if row is None: raise FinancingPreauthError("PREAUTH_NOT_FOUND")
    if row.status not in {"PENDING","SUBMITTED"}: raise FinancingPreauthError("PREAUTH_NOT_DECIDABLE")
    approved=Decimal(str(payload.approved_amount)).quantize(Decimal("0.01"))
    requested=Decimal(str(row.requested_amount)).quantize(Decimal("0.01"))
    if approved > requested: raise FinancingPreauthError("APPROVED_AMOUNT_EXCEEDS_REQUEST")
    if payload.status=="REJECTED" and approved != 0: raise FinancingPreauthError("REJECTED_AMOUNT_MUST_BE_ZERO")
    if payload.status in {"AUTHORIZED","CONDITIONAL"} and approved == 0: raise FinancingPreauthError("INVALID_APPROVED_AMOUNT")
    row.status=payload.status; row.approved_amount=approved; row.external_reference=payload.external_reference.strip() if payload.external_reference else None; row.decided_at=datetime.now(timezone.utc)
    record_audit(db, action="FINANCING_PREAUTH_DECIDED", resource_type="FINANCING_PREAUTHORIZATION", resource_id=str(row.id), result=payload.status, user_id=actor_user_id, facility_id=facility_id, patient_id=row.person_id, metadata={"approved_amount":str(approved),"external_reference":row.external_reference}, commit=False)
    db.commit(); db.refresh(row); return row
