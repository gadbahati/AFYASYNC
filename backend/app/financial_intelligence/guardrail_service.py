from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from app.audit.service import record_audit
from app.claims.models import Claim, ClaimItem
from app.adjudication.models import ClaimAdjudication
from app.provider_network.models import ProviderNetworkContract, ProviderNetworkMembership, ProviderNetworkService
from app.financial_intelligence.guardrail_models import ContractComplianceGuardrail, ContractComplianceGuardrailEvent

ACTIVE={"ACTIVE"}
TERMINAL={"PAID","SETTLED","CLOSED","RECONCILED"}

def _active_contract(db,facility_id,payer_networks):
    if not payer_networks: return None
    return db.scalar(select(ProviderNetworkContract).where(
        ProviderNetworkContract.facility_id==facility_id,
        ProviderNetworkContract.network_code.in_(payer_networks),
        ProviderNetworkContract.status=="ACTIVE",
        ProviderNetworkContract.execution_status=="EXECUTED",
        ProviderNetworkContract.activation_status.in_([ "ACTIVATED","PARTIAL" ]),
    ).order_by(ProviderNetworkContract.effective_from.desc().nullslast()))

def _severity(amount):
    amount=Decimal(amount or 0)
    if amount>=Decimal("100000"): return "CRITICAL"
    if amount>=Decimal("25000"): return "HIGH"
    if amount>0: return "MEDIUM"
    return "LOW"

def _expected_tariff(db,facility_id,network_code,claim_id):
    rows=db.execute(select(ClaimItem.service_code,ClaimItem.quantity,ProviderNetworkService.tariff_amount).join(ProviderNetworkService,(
        ProviderNetworkService.facility_id==facility_id)&
        (ProviderNetworkService.network_code==network_code)&
        (ProviderNetworkService.service_code==ClaimItem.service_code)
    ).where(ClaimItem.claim_id==claim_id,ProviderNetworkService.status=="ACTIVE")).all()
    expected=Decimal("0"); missing=[]
    for code,qty,tariff in rows:
        if tariff is None: missing.append(code); continue
        expected += Decimal(tariff)*Decimal(qty)
    return expected,missing,len(rows)

def _upsert(db,facility_id,contract,claim,gtype,severity,title,expected,actual,risk,detail,evidence,actor_id):
    existing=db.scalar(select(ContractComplianceGuardrail).where(
        ContractComplianceGuardrail.facility_id==facility_id,
        ContractComplianceGuardrail.claim_id==claim.id,
        ContractComplianceGuardrail.guardrail_type==gtype,
        ContractComplianceGuardrail.status!="RESOLVED",
    ))
    if existing:
        existing.expected_amount=expected; existing.actual_amount=actual; existing.amount_at_risk=risk
        existing.detail=detail; existing.evidence=evidence; existing.severity=severity
        return existing,False
    row=ContractComplianceGuardrail(
        facility_id=facility_id,contract_id=contract.id if contract else None,claim_id=claim.id,
        payer_id=claim.payer_id,guardrail_type=gtype,severity=severity,status="OPEN",
        title=title,expected_amount=expected,actual_amount=actual,amount_at_risk=risk,detail=detail,evidence=evidence)
    db.add(row); db.flush()
    db.add(ContractComplianceGuardrailEvent(guardrail_id=row.id,event_type="CREATED",to_status="OPEN",actor_id=actor_id,note=detail,metadata_json=evidence))
    return row,True

def sync_guardrails(db:Session,facility_id:UUID,actor_id:UUID,limit:int=200):
    claims=db.scalars(select(Claim).where(Claim.invoice_id.is_not(None),Claim.status!="DRAFT").order_by(Claim.updated_at.desc()).limit(max(1,min(limit,500)))).all()
    created=0; checked=0
    for claim in claims:
        membership=db.scalar(select(ProviderNetworkMembership).where(ProviderNetworkMembership.facility_id==facility_id,ProviderNetworkMembership.claims_enabled==True).limit(1))
        if not membership: continue
        contract=_active_contract(db,facility_id,[membership.network_code])
        if not contract: continue
        checked+=1
        expected,missing,line_count=_expected_tariff(db,facility_id,contract.network_code,claim.id)
        if line_count==0: continue
        if missing:
            _,new=_upsert(db,facility_id,contract,claim,"TARIFF_CONFIGURATION_GAP","HIGH","Contract tariff configuration gap",expected,claim.claim_amount,Decimal("0"),"One or more claim services have no active contracted tariff.",{"missing_service_codes":missing},actor_id); created+=int(new)
        elif claim.claim_amount>expected:
            risk=claim.claim_amount-expected
            _,new=_upsert(db,facility_id,contract,claim,"TARIFF_BREACH",_severity(risk),"Claim exceeds activated contract tariff",expected,claim.claim_amount,risk,"Submitted claim value exceeds the activated contract tariff envelope.",{"contract_id":str(contract.id),"network_code":contract.network_code},actor_id); created+=int(new)
        adj=db.scalar(select(ClaimAdjudication).where(ClaimAdjudication.claim_id==claim.id))
        if adj and adj.allowed_amount<expected:
            risk=expected-adj.allowed_amount
            _,new=_upsert(db,facility_id,contract,claim,"ADJUDICATION_VARIANCE",_severity(risk),"Adjudication below contracted tariff value",expected,adj.allowed_amount,risk,"Adjudicated allowed amount is below the activated contract tariff value.",{"decision":adj.decision,"reason_code":adj.reason_code},actor_id); created+=int(new)
        if claim.status in TERMINAL and claim.paid_amount<claim.approved_amount:
            risk=claim.approved_amount-claim.paid_amount
            _,new=_upsert(db,facility_id,contract,claim,"PAYMENT_VARIANCE",_severity(risk),"Payment below approved claim amount",claim.approved_amount,claim.paid_amount,risk,"Terminal claim has an approved-to-paid variance requiring reconciliation/recovery review.",{"claim_status":claim.status},actor_id); created+=int(new)
    record_audit(db,actor_id,"SYNC_CONTRACT_COMPLIANCE_GUARDRAILS","contract_compliance_guardrails",str(facility_id),{"checked":checked,"created":created})
    db.commit()
    return {"checked":checked,"created":created,"summary":overview(db,facility_id)}

def overview(db:Session,facility_id:UUID):
    rows=db.execute(select(ContractComplianceGuardrail.status,ContractComplianceGuardrail.severity,func.count(ContractComplianceGuardrail.id),func.coalesce(func.sum(ContractComplianceGuardrail.amount_at_risk),0)).where(ContractComplianceGuardrail.facility_id==facility_id).group_by(ContractComplianceGuardrail.status,ContractComplianceGuardrail.severity)).all()
    return {"statuses":{f"{s}:{sev}":{"count":int(c),"amount_at_risk":float(a or 0)} for s,sev,c,a in rows},
            "total":int(db.scalar(select(func.count(ContractComplianceGuardrail.id)).where(ContractComplianceGuardrail.facility_id==facility_id)) or 0),
            "open":int(db.scalar(select(func.count(ContractComplianceGuardrail.id)).where(ContractComplianceGuardrail.facility_id==facility_id,ContractComplianceGuardrail.status!="RESOLVED")) or 0),
            "at_risk":float(db.scalar(select(func.coalesce(func.sum(ContractComplianceGuardrail.amount_at_risk),0)).where(ContractComplianceGuardrail.facility_id==facility_id,ContractComplianceGuardrail.status!="RESOLVED")) or 0)}

def list_guardrails(db:Session,facility_id:UUID,status:str|None=None,limit:int=200):
    q=select(ContractComplianceGuardrail).where(ContractComplianceGuardrail.facility_id==facility_id)
    if status: q=q.where(ContractComplianceGuardrail.status==status)
    return db.scalars(q.order_by(ContractComplianceGuardrail.severity.desc(),ContractComplianceGuardrail.created_at.desc()).limit(max(1,min(limit,500)))).all()

def update_guardrail(db:Session,facility_id:UUID,guardrail_id:UUID,status:str,actor_id:UUID,note:str|None=None):
    if status not in {"OPEN","IN_REVIEW","RESOLVED","DISMISSED"}: raise ValueError("INVALID_GUARDRAIL_STATUS")
    row=db.scalar(select(ContractComplianceGuardrail).where(ContractComplianceGuardrail.id==guardrail_id,ContractComplianceGuardrail.facility_id==facility_id))
    if not row: raise ValueError("GUARDRAIL_NOT_FOUND")
    old=row.status; row.status=status
    if status in {"RESOLVED","DISMISSED"}: row.resolved_at=datetime.now(timezone.utc)
    db.add(ContractComplianceGuardrailEvent(guardrail_id=row.id,event_type="STATUS_CHANGED",from_status=old,to_status=status,actor_id=actor_id,note=note))
    record_audit(db,actor_id,"UPDATE_CONTRACT_GUARDRAIL","contract_compliance_guardrail",str(row.id),{"from":old,"to":status})
    db.commit(); db.refresh(row); return row

def events(db:Session,facility_id:UUID,guardrail_id:UUID):
    valid=db.scalar(select(ContractComplianceGuardrail.id).where(ContractComplianceGuardrail.id==guardrail_id,ContractComplianceGuardrail.facility_id==facility_id))
    if not valid: raise ValueError("GUARDRAIL_NOT_FOUND")
    return db.scalars(select(ContractComplianceGuardrailEvent).where(ContractComplianceGuardrailEvent.guardrail_id==guardrail_id).order_by(ContractComplianceGuardrailEvent.created_at.desc())).all()
