"""Phase 169: consent lifecycle and Kenya Core FHIR Consent projection."""
from datetime import datetime, timezone
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.audit.service import record_audit
from app.hie.consent_models import HieConsent
from app.hie.models import HieNode\nfrom app.patients.models import PatientFacility

def create_consent(db: Session, *, patient_id: UUID, facility_id: UUID, recipient_node_id: UUID|None, purpose: str, period_start: datetime|None, period_end: datetime|None, created_by: UUID, evidence: dict|None=None) -> HieConsent:
    if recipient_node_id is not None:
        node=db.get(HieNode,recipient_node_id)
        if node is None or node.status!="ACTIVE": raise ValueError("HIE_RECIPIENT_NOT_FOUND")
    if period_start and period_end and period_end <= period_start: raise ValueError("HIE_CONSENT_INVALID_PERIOD")
    resource={
        "resourceType":"Consent","status":"active","scope":{"coding":[{"system":"http://terminology.hl7.org/CodeSystem/consentscope","code":"patient-privacy"}]},
        "category":[{"text":"Health information sharing consent"}],
        "patient":{"reference":f"Patient/{patient_id}"},
        "dateTime":datetime.now(timezone.utc).isoformat(),
        "provision":{"type":"permit","purpose":[{"text":purpose}]}
    }
    if period_start or period_end: resource["provision"]["period"]={k:v.isoformat() for k,v in {"start":period_start,"end":period_end}.items() if v}
    c=HieConsent(patient_id=patient_id,facility_id=facility_id,recipient_node_id=recipient_node_id,status="ACTIVE",decision="PERMIT",purpose=purpose,scope="HIE_SHARE",period_start=period_start,period_end=period_end,evidence=evidence or {},fhir_resource=resource,created_by=created_by)
    db.add(c); db.flush()
    record_audit(db,action="HIE_CONSENT_GRANTED",resource_type="HIE_CONSENT",resource_id=str(c.id),result="SUCCESS",user_id=created_by,facility_id=facility_id,patient_id=patient_id,metadata={"recipient_node_id":str(recipient_node_id) if recipient_node_id else None,"purpose":purpose},commit=False)
    return c

def revoke_consent(db: Session, *, consent_id: UUID, facility_id: UUID, actor_user_id: UUID) -> HieConsent:
    c=db.get(HieConsent,consent_id)
    if c is None or c.facility_id!=facility_id: raise ValueError("HIE_CONSENT_NOT_FOUND")
    c.status="REVOKED"; c.revoked_at=datetime.now(timezone.utc); c.fhir_resource={**c.fhir_resource,"status":"inactive"}
    record_audit(db,action="HIE_CONSENT_REVOKED",resource_type="HIE_CONSENT",resource_id=str(c.id),result="SUCCESS",user_id=actor_user_id,facility_id=facility_id,patient_id=c.patient_id,metadata={},commit=False)
    db.flush(); return c

def list_consents(db: Session, *, patient_id: UUID, facility_id: UUID):
    return list(db.scalars(select(HieConsent).where(HieConsent.patient_id==patient_id,HieConsent.facility_id==facility_id).order_by(HieConsent.created_at.desc())))
