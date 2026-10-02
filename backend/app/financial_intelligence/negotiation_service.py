from datetime import datetime,timezone
from uuid import UUID
from sqlalchemy import select,func
from sqlalchemy.orm import Session
from app.provider_network.models import ProviderNetworkContract,ProviderNetworkMembership,ProviderNetworkService
from app.coverage.models import Payer
from app.financial_intelligence.negotiation_models import PayerNegotiationCase,PayerNegotiationItem,PayerNegotiationEvent
from app.financial_intelligence.payer_command import payer_command
from app.financial_intelligence.tariff_intelligence import tariff_intelligence
from app.financial_intelligence.contract_renewal import contract_renewal_intelligence

STATUSES={"DRAFT","INTERNAL_REVIEW","READY_TO_SEND","SENT","IN_NEGOTIATION","AGREED","APPROVED","CLOSED","CANCELLED"}
ITEM_TYPES={"TARIFF","PAYMENT_TERMS","SLA","CLAIMS_WORKFLOW","EMPANELMENT","OTHER"}

def _case(db,cid,facility_id):
    c=db.scalar(select(PayerNegotiationCase).where(PayerNegotiationCase.id==cid,PayerNegotiationCase.facility_id==facility_id))
    if not c: raise ValueError("NEGOTIATION_CASE_NOT_FOUND")
    return c

def _out(c):
    return {"id":str(c.id),"case_number":c.case_number,"contract_id":str(c.contract_id),"status":c.status,"owner_id":str(c.owner_id) if c.owner_id else None,"due_at":c.due_at.isoformat() if c.due_at else None,"objective":c.objective,"opening_position":c.opening_position,"target_position":c.target_position,"evidence_snapshot":c.evidence_snapshot,"proposed_terms":c.proposed_terms,"accepted_terms":c.accepted_terms,"notes":c.notes,"created_at":c.created_at.isoformat() if c.created_at else None,"updated_at":c.updated_at.isoformat() if c.updated_at else None,"closed_at":c.closed_at.isoformat() if c.closed_at else None}

def _snapshot(db,facility_id,contract_id):
    c=db.scalar(select(ProviderNetworkContract).where(ProviderNetworkContract.id==contract_id,ProviderNetworkContract.facility_id==facility_id))
    if not c: raise ValueError("CONTRACT_NOT_FOUND")
    payer=db.scalar(select(Payer).where(Payer.code==c.network_code))
    renewal=contract_renewal_intelligence(db,facility_id,180)
    row=next((x for x in renewal["contracts"] if x["contract_id"]==str(contract_id)),None)
    payers=payer_command(db,facility_id,90).get("payers",[])
    payer_row=next((x for x in payers if payer and (x.get("payer_code")==c.network_code or x.get("payer_id")==str(payer.id))),None)
    tariffs=tariff_intelligence(db,facility_id,90,30)
    tariff_rows=[x for x in tariffs.get("services",[]) if x.get("payer_name")==(payer.name if payer else c.network_code)][:10]
    return {"captured_at":datetime.now(timezone.utc).isoformat(),"contract":{"id":str(c.id),"reference":c.contract_reference,"status":c.status,"payment_terms_days":c.payment_terms_days,"renewal_due_at":c.renewal_due_at.isoformat() if c.renewal_due_at else None},"payer":{"id":str(payer.id) if payer else None,"code":c.network_code,"name":payer.name if payer else c.network_code},"renewal":row,"payer_performance":payer_row,"tariff_evidence":tariff_rows}

def create_case(db,facility_id,contract_id,actor_id,objective=None,due_at=None):
    c=db.scalar(select(ProviderNetworkContract).where(ProviderNetworkContract.id==contract_id,ProviderNetworkContract.facility_id==facility_id))
    if not c: raise ValueError("CONTRACT_NOT_FOUND")
    active=db.scalar(select(PayerNegotiationCase).where(PayerNegotiationCase.contract_id==contract_id,PayerNegotiationCase.facility_id==facility_id,PayerNegotiationCase.status.notin_({"CLOSED","CANCELLED"})))
    if active: return active
    snap=_snapshot(db,facility_id,contract_id)
    seq=int(db.scalar(select(func.count(PayerNegotiationCase.id)).where(PayerNegotiationCase.facility_id==facility_id)) or 0)+1
    case=PayerNegotiationCase(facility_id=facility_id,contract_id=contract_id,case_number=f"NEG-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{seq:04d}",owner_id=actor_id,due_at=due_at,objective=objective,evidence_snapshot=snap,opening_position={"payment_terms_days":c.payment_terms_days},target_position={"payment_terms_days":max(0,c.payment_terms_days-15)})
    db.add(case);db.flush()
    db.add(PayerNegotiationEvent(case_id=case.id,event_type="CASE_CREATED",to_status=case.status,actor_id=actor_id,note="Negotiation workspace created from current contract and performance evidence"))
    db.commit();db.refresh(case);return case

def list_cases(db,facility_id,status=None):
    q=select(PayerNegotiationCase).where(PayerNegotiationCase.facility_id==facility_id).order_by(PayerNegotiationCase.updated_at.desc())
    if status:q=q.where(PayerNegotiationCase.status==status)
    return list(db.scalars(q).all())

def update_case(db,facility_id,cid,actor_id,**changes):
    c=_case(db,cid,facility_id); old=c.status
    for k,v in changes.items():
        if v is not None and hasattr(c,k):setattr(c,k,v)
    if c.status not in STATUSES: raise ValueError("INVALID_NEGOTIATION_STATUS")
    if c.status in {"CLOSED","CANCELLED"}:c.closed_at=datetime.now(timezone.utc)
    db.add(PayerNegotiationEvent(case_id=c.id,event_type="CASE_UPDATED",from_status=old,to_status=c.status,actor_id=actor_id,note=changes.get("notes")))
    db.commit();db.refresh(c);return c

def add_item(db,facility_id,cid,actor_id,item_type,title,current_value=None,requested_value=None,rationale=None,priority="MEDIUM"):
    c=_case(db,cid,facility_id)
    if item_type not in ITEM_TYPES:raise ValueError("INVALID_NEGOTIATION_ITEM_TYPE")
    item=PayerNegotiationItem(case_id=c.id,item_type=item_type,title=title,current_value=current_value,requested_value=requested_value,rationale=rationale,priority=priority)
    db.add(item);db.add(PayerNegotiationEvent(case_id=c.id,event_type="ITEM_ADDED",to_status=c.status,actor_id=actor_id,note=title));db.commit();db.refresh(item);return item

def update_item(db,facility_id,item_id,actor_id,**changes):
    item=db.scalar(select(PayerNegotiationItem).join(PayerNegotiationCase,PayerNegotiationCase.id==PayerNegotiationItem.case_id).where(PayerNegotiationItem.id==item_id,PayerNegotiationCase.facility_id==facility_id))
    if not item:raise ValueError("NEGOTIATION_ITEM_NOT_FOUND")
    for k,v in changes.items():
        if v is not None and hasattr(item,k):setattr(item,k,v)
    db.add(PayerNegotiationEvent(case_id=item.case_id,event_type="ITEM_UPDATED",actor_id=actor_id,note=item.title));db.commit();db.refresh(item);return item

def items(db,facility_id,cid):
    _case(db,cid,facility_id)
    return list(db.scalars(select(PayerNegotiationItem).where(PayerNegotiationItem.case_id==cid).order_by(PayerNegotiationItem.priority.desc(),PayerNegotiationItem.created_at)).all())

def overview(db,facility_id):
    rows=list_cases(db,facility_id)
    return {"total":len(rows),"draft":sum(x.status=="DRAFT" for x in rows),"active":sum(x.status in {"INTERNAL_REVIEW","READY_TO_SEND","SENT","IN_NEGOTIATION"} for x in rows),"agreed":sum(x.status in {"AGREED","APPROVED"} for x in rows),"overdue":sum(bool(x.due_at and x.due_at<datetime.now(timezone.utc) and x.status not in {"CLOSED","CANCELLED","APPROVED"}) for x in rows)}

def events(db,facility_id,cid):
    _case(db,cid,facility_id)
    return list(db.scalars(select(PayerNegotiationEvent).where(PayerNegotiationEvent.case_id==cid).order_by(PayerNegotiationEvent.created_at.desc())).all())
