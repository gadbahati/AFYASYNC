from datetime import datetime,timezone
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.coverage.models import Payer
from app.provider_network.models import ProviderNetworkContract,ProviderNetworkMembership,ProviderNetworkService
from app.financial_intelligence.sla_models import PayerSLAPolicy
from app.financial_intelligence.negotiation_models import PayerNegotiationCase
from app.financial_intelligence.activation_models import ContractActivationEvent

def _contract(db,facility_id,contract_id):
    c=db.scalar(select(ProviderNetworkContract).where(ProviderNetworkContract.id==contract_id,ProviderNetworkContract.facility_id==facility_id))
    if not c: raise ValueError("CONTRACT_NOT_FOUND")
    return c

def _terms(db,facility_id,c):
    terms=c.executed_terms
    if terms:
        return terms
    case=db.scalar(select(PayerNegotiationCase).where(
        PayerNegotiationCase.contract_id==c.id,
        PayerNegotiationCase.facility_id==facility_id,
        PayerNegotiationCase.status.in_({"AGREED","APPROVED"})
    ).order_by(PayerNegotiationCase.updated_at.desc()))
    return case.accepted_terms if case and case.accepted_terms else {}

def _event(db,facility_id,contract_id,actor_id,event_type,status,details):
    db.add(ContractActivationEvent(facility_id=facility_id,contract_id=contract_id,event_type=event_type,status=status,actor_id=actor_id,details=details))

def activate_contract(db:Session,facility_id:UUID,contract_id:UUID,actor_id:UUID,override_terms=None):
    c=_contract(db,facility_id,contract_id)
    if c.execution_status!="EXECUTED" or c.status!="ACTIVE":
        raise ValueError("CONTRACT_NOT_EXECUTED")
    terms=override_terms if override_terms is not None else _terms(db,facility_id,c)
    if not isinstance(terms,dict):
        raise ValueError("INVALID_EXECUTED_TERMS")

    applied=[];skipped=[];errors=[]
    network=c.network_code
    tariff_rows=terms.get("tariffs",terms.get("services",[])) or []
    if isinstance(tariff_rows,dict):
        tariff_rows=[{"service_code":k,**(v if isinstance(v,dict) else {"amount":v})} for k,v in tariff_rows.items()]
    for row in tariff_rows:
        if not isinstance(row,dict): skipped.append({"type":"TARIFF","reason":"INVALID_ROW"});continue
        code=str(row.get("service_code") or row.get("code") or "").strip()
        amount=row.get("amount",row.get("tariff_amount",row.get("unit_amount")))
        if not code or amount is None:
            skipped.append({"type":"TARIFF","reason":"MISSING_SERVICE_CODE_OR_AMOUNT","row":row});continue
        try:
            svc=db.scalar(select(ProviderNetworkService).where(
                ProviderNetworkService.facility_id==facility_id,
                ProviderNetworkService.network_code==network,
                ProviderNetworkService.service_code==code
            ))
            if not svc:
                svc=ProviderNetworkService(facility_id=facility_id,network_code=network,service_code=code,service_name=str(row.get("service_name") or code),status="ACTIVE",tariff_amount=amount,currency=str(row.get("currency") or "KES"))
                db.add(svc);db.flush();action="CREATED"
            else:
                changed=svc.tariff_amount!=amount or (row.get("currency") and svc.currency!=row.get("currency")) or svc.status!="ACTIVE"
                if changed:
                    svc.tariff_amount=amount
                    if row.get("currency"): svc.currency=str(row["currency"])
                    svc.status="ACTIVE"
                    action="UPDATED"
                else: action="ALREADY_ACTIVE"
            applied.append({"type":"TARIFF","service_code":code,"amount":float(amount),"action":action})
        except Exception as e:
            errors.append({"type":"TARIFF","service_code":code,"error":str(e)})

    payment_terms=terms.get("payment_terms_days",terms.get("payment_terms"))
    if isinstance(payment_terms,dict): payment_terms=payment_terms.get("days")
    if payment_terms is not None:
        try:
            c.payment_terms_days=int(payment_terms)
            applied.append({"type":"PAYMENT_TERMS","days":c.payment_terms_days})
        except Exception as e: errors.append({"type":"PAYMENT_TERMS","error":str(e)})

    payer=db.scalar(select(Payer).where(Payer.code==network))
    sla=terms.get("sla") or terms.get("SLA")
    if isinstance(sla,dict) and payer:
        policy=db.scalar(select(PayerSLAPolicy).where(PayerSLAPolicy.facility_id==facility_id,PayerSLAPolicy.payer_id==payer.id))
        if not policy:
            policy=PayerSLAPolicy(facility_id=facility_id,payer_id=payer.id);db.add(policy);db.flush()
        mapping={"denial_response_hours":"denial_response_hours","resolution_hours":"resolution_hours","appeal_hours":"appeal_hours","escalation_hours":"escalation_hours"}
        for key,field in mapping.items():
            if sla.get(key) is not None: setattr(policy,field,int(sla[key]))
        policy.active=bool(sla.get("active",True))
        if sla.get("notes") is not None: policy.notes=str(sla["notes"])
        applied.append({"type":"SLA","payer_id":str(payer.id),"action":"UPSERTED"})
    elif isinstance(sla,dict) and not payer:
        skipped.append({"type":"SLA","reason":"PAYER_NOT_FOUND","network_code":network})

    claims_enabled=terms.get("claims_enabled")
    if claims_enabled is None and isinstance(terms.get("claims_workflow"),dict):
        claims_enabled=terms["claims_workflow"].get("enabled")
    membership=db.scalar(select(ProviderNetworkMembership).where(ProviderNetworkMembership.facility_id==facility_id,ProviderNetworkMembership.network_code==network))
    if claims_enabled is not None:
        if membership:
            membership.claims_enabled=bool(claims_enabled)
            applied.append({"type":"CLAIMS_WORKFLOW","claims_enabled":membership.claims_enabled})
        else:
            skipped.append({"type":"CLAIMS_WORKFLOW","reason":"MEMBERSHIP_NOT_FOUND","network_code":network})

    empanelment=terms.get("empanelment") or terms.get("network") or {}
    if isinstance(empanelment,dict):
        participation=empanelment.get("participation_status") or empanelment.get("status")
        if participation and membership:
            membership.participation_status=str(participation)
            if empanelment.get("effective_from"): membership.effective_from=datetime.fromisoformat(str(empanelment["effective_from"]).replace("Z","+00:00"))
            if empanelment.get("effective_to"): membership.effective_to=datetime.fromisoformat(str(empanelment["effective_to"]).replace("Z","+00:00"))
            applied.append({"type":"EMPANELMENT","status":membership.participation_status})
        elif participation and not membership:
            skipped.append({"type":"EMPANELMENT","reason":"MEMBERSHIP_NOT_FOUND","network_code":network})

    if errors: status="PARTIAL"
    elif applied: status="ACTIVATED"
    else: status="NO_APPLICABLE_TERMS"
    summary={"status":status,"applied":applied,"skipped":skipped,"errors":errors,"term_keys":sorted(terms.keys())}
    c.activation_status=status
    c.activated_at=datetime.now(timezone.utc) if status in {"ACTIVATED","PARTIAL"} else c.activated_at
    c.activation_summary=summary
    _event(db,facility_id,c.id,actor_id,"CONTRACT_ACTIVATED",status,summary)
    db.commit();db.refresh(c)
    return {"contract_id":str(c.id),"contract_reference":c.contract_reference,"network_code":network,"activation_status":status,"activated_at":c.activated_at.isoformat() if c.activated_at else None,"summary":summary}

def overview(db:Session,facility_id:UUID):
    rows=list(db.scalars(select(ProviderNetworkContract).where(ProviderNetworkContract.facility_id==facility_id)).all())
    return {"total":len(rows),"not_activated":sum(x.activation_status=="NOT_ACTIVATED" for x in rows),"activated":sum(x.activation_status=="ACTIVATED" for x in rows),"partial":sum(x.activation_status=="PARTIAL" for x in rows),"no_terms":sum(x.activation_status=="NO_APPLICABLE_TERMS" for x in rows)}

def events(db:Session,facility_id:UUID,contract_id:UUID):
    _contract(db,facility_id,contract_id)
    return list(db.scalars(select(ContractActivationEvent).where(ContractActivationEvent.contract_id==contract_id).order_by(ContractActivationEvent.created_at.desc())).all())
