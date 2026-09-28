from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.audit.service import record_audit
from app.fraud_integrity.case_models import FraudIntegrityCase
from app.fraud_integrity.service import facility_integrity_scan

class FraudCaseError(ValueError): pass

def create_case(db: Session, *, facility_id: UUID, actor_user_id: UUID, signal: dict):
    claim_id = signal.get("claim_id")
    patient_id = signal.get("patient_id")
    payer_id = signal.get("payer_id")
    case = FraudIntegrityCase(
        case_number=f"FXFI-{datetime.now(timezone.utc):%Y%m%d}-{uuid4().hex[:10].upper()}",
        facility_id=facility_id,
        claim_id=UUID(str(claim_id)) if claim_id and len(str(claim_id)) == 36 else None,
        patient_id=UUID(str(patient_id)) if patient_id and len(str(patient_id)) == 36 else None,
        payer_id=UUID(str(payer_id)) if payer_id and len(str(payer_id)) == 36 else None,
        signal_code=str(signal.get("code","UNSPECIFIED")),
        severity=str(signal.get("severity","MEDIUM")),
        summary=str(signal.get("message","Integrity signal requires review")),
        evidence=signal,
        status="OPEN",
    )
    db.add(case); db.flush()
    record_audit(db, actor_user_id, "CREATE_FRAUD_INTEGRITY_CASE", "fraud_integrity_case", str(case.id), {"signal_code": case.signal_code})
    db.commit(); db.refresh(case); return case

def list_cases(db: Session, facility_id: UUID, status: str | None = None):
    q=select(FraudIntegrityCase).where(FraudIntegrityCase.facility_id==facility_id)
    if status: q=q.where(FraudIntegrityCase.status==status)
    return list(db.scalars(q.order_by(FraudIntegrityCase.created_at.desc()).limit(200)).all())

def resolve_case(db: Session, *, facility_id: UUID, case_id: UUID, actor_user_id: UUID, status: str, note: str):
    case=db.get(FraudIntegrityCase,case_id)
    if case is None or case.facility_id != facility_id: raise FraudCaseError("CASE_NOT_FOUND")
    if status not in {"CONFIRMED","DISMISSED","MONITORING"}: raise FraudCaseError("INVALID_CASE_STATUS")
    case.status=status; case.resolution_note=note; case.resolved_at=datetime.now(timezone.utc)
    record_audit(db,actor_user_id,"RESOLVE_FRAUD_INTEGRITY_CASE","fraud_integrity_case",str(case.id),{"status":status})
    db.commit(); db.refresh(case); return case
