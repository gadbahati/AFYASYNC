from datetime import datetime,timezone
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.provider_network.models import ProviderNetworkContract,ProviderContractEvent
from app.financial_intelligence.negotiation_models import PayerNegotiationCase
from app.financial_intelligence.execution_models import ContractExecutionApproval,ContractExecutionEvent

def _contract(db,facility_id,cid):
    c=db.scalar(select(ProviderNetworkContract).where(ProviderNetworkContract.id==cid,ProviderNetworkContract.facility_id==facility_id))
    if not c: raise ValueError("CONTRACT_NOT_FOUND")
    return c

def request_execution(db,facility_id,contract_id,negotiation_case_id,actor_id,terms=None,notes=None):
    c=_contract(db,facility_id,contract_id)
    if negotiation_case_id:
        n=db.scalar(select(PayerNegotiationCase).where(PayerNegotiationCase.id==negotiation_case_id,PayerNegotiationCase.facility_id==facility_id))
        if not n: raise ValueError("NEGOTIATION_CASE_NOT_FOUND")
        if n.status not in {"AGREED","APPROVED"}: raise ValueError("NEGOTIATION_NOT_AGREED")
    if c.execution_status=="EXECUTED": raise ValueError("CONTRACT_ALREADY_EXECUTED")
    a=ContractExecutionApproval(facility_id=facility_id,contract_id=c.id,negotiation_case_id=negotiation_case_id,requested_by=actor_id,requested_terms=terms,review_notes=notes)
    c.execution_status="PENDING_APPROVAL"
    db.add(a);db.flush()
    db.add(ContractExecutionEvent(contract_id=c.id,approval_id=a.id,event_type="EXECUTION_REQUESTED",actor_id=actor_id,notes=notes,metadata={"terms":terms or {}}))
    db.commit();db.refresh(a);return a

def review_execution(db,facility_id,approval_id,actor_id,status,notes=None):
    a=db.scalar(select(ContractExecutionApproval).where(ContractExecutionApproval.id==approval_id,ContractExecutionApproval.facility_id==facility_id))
    if not a: raise ValueError("APPROVAL_NOT_FOUND")
    if status not in {"APPROVED","REJECTED"}: raise ValueError("INVALID_APPROVAL_STATUS")
    c=_contract(db,facility_id,a.contract_id)
    a.status=status;a.reviewed_by=actor_id;a.reviewed_at=datetime.now(timezone.utc);a.review_notes=notes
    if status=="APPROVED":
        c.execution_status="READY_TO_EXECUTE"
    else:
        c.execution_status="REJECTED"
    db.add(ContractExecutionEvent(contract_id=c.id,approval_id=a.id,event_type="EXECUTION_APPROVAL_REVIEWED",actor_id=actor_id,notes=notes,metadata={"status":status}))
    db.commit();db.refresh(a);return a

def execute_contract(db,facility_id,contract_id,actor_id,execution_reference=None,terms=None,notes=None):
    c=_contract(db,facility_id,contract_id)
    if c.execution_status!="READY_TO_EXECUTE": raise ValueError("CONTRACT_NOT_READY_FOR_EXECUTION")
    now=datetime.now(timezone.utc)
    c.execution_status="EXECUTED";c.executed_at=now;c.execution_reference=execution_reference;c.executed_terms=terms;c.execution_notes=notes
    c.status="ACTIVE";c.effective_from=c.effective_from or now;c.accepted_at=c.accepted_at or now;c.accepted_by=actor_id
    db.add(ProviderContractEvent(contract_id=c.id,event_type="CONTRACT_EXECUTED",from_status="READY_TO_EXECUTE",to_status="ACTIVE",actor_id=actor_id,notes=notes,metadata={"execution_reference":execution_reference,"terms":terms or {}}))
    db.add(ContractExecutionEvent(contract_id=c.id,event_type="CONTRACT_EXECUTED",actor_id=actor_id,notes=notes,metadata={"execution_reference":execution_reference}))
    db.commit();db.refresh(c);return c

def overview(db,facility_id):
    rows=list(db.scalars(select(ProviderNetworkContract).where(ProviderNetworkContract.facility_id==facility_id)).all())
    return {"total":len(rows),"pending_approval":sum(x.execution_status=="PENDING_APPROVAL" for x in rows),"ready":sum(x.execution_status=="READY_TO_EXECUTE" for x in rows),"executed":sum(x.execution_status=="EXECUTED" for x in rows),"rejected":sum(x.execution_status=="REJECTED" for x in rows)}
