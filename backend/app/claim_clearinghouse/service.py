from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID, uuid4
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from app.audit.service import record_audit
from app.claims.models import Claim
from app.coverage.models import Payer
from app.integrations.models import Integration
from app.integrations.service import IntegrationError, queue_transaction
from app.claim_clearinghouse.models import ClearinghouseCase, ClearinghouseEvent, ClearinghouseRoute, ClearinghouseDenialCode, ClearinghouseRemittance

SOURCE_TYPES={"SHA","PRIVATE_INSURER","EMPLOYER_SCHEME","COUNTY_PROGRAM","SELF_PAY"}
STATUSES={"INTAKE","VALIDATING","READY","QUEUED","SUBMITTED","ACKNOWLEDGED","IN_REVIEW","ACCEPTED","PARTIALLY_PAID","REJECTED","PAID","RECONCILED","FAILED"}
DENIALS={
 "AUTHORIZATION":"AUTHORIZATION","ELIGIBILITY":"ELIGIBILITY","DOCUMENTATION":"DOCUMENTATION",
 "DUPLICATE":"DUPLICATE","CODING":"CODING","TARIFF":"TARIFF","TIMING":"TIMING","CLINICAL":"CLINICAL",
 "TECHNICAL":"TECHNICAL","OTHER":"OTHER"
}

class ClearinghouseError(ValueError): pass

def _number(): return f"CH-{datetime.now(timezone.utc):%Y%m%d}-{uuid4().hex[:10].upper()}"

def _source(payer:Payer|None, claim:Claim) -> str:
    code=(payer.code or "").upper() if payer else ""
    if code in {"SHA","SHIF","PHF","ECCIF"} or getattr(claim,"coverage_mode",None)=="SHA": return "SHA"
    if code.startswith("COUNTY") or code in {"MFL","COUNTY"}: return "COUNTY_PROGRAM"
    if code.startswith("EMP") or "EMPLOY" in code: return "EMPLOYER_SCHEME"
    if not payer or code in {"CASH","SELF_PAY"}: return "SELF_PAY"
    return "PRIVATE_INSURER"

def _route(db, facility_id, payer_id, source_type):
    q=select(ClearinghouseRoute).where(ClearinghouseRoute.facility_id==facility_id,ClearinghouseRoute.active.is_(True),ClearinghouseRoute.source_type==source_type)
    if payer_id is not None: q=q.where((ClearinghouseRoute.payer_id==payer_id)|(ClearinghouseRoute.payer_id.is_(None)))
    return db.scalar(q.order_by(ClearinghouseRoute.priority.asc()).limit(1))

def _event(db, case, event_type, actor_id=None, to_status=None, message=None, metadata=None):
    db.add(ClearinghouseEvent(case_id=case.id,event_type=event_type,from_status=case.status,to_status=to_status,actor_id=actor_id,message=message,event_metadata=metadata))
    if to_status: case.status=to_status

def create_case(db:Session, facility_id:UUID, claim_id:UUID|None, idempotency_key:str, actor_id:UUID|None=None, invoice_id:UUID|None=None)->ClearinghouseCase:
    existing=db.scalar(select(ClearinghouseCase).where(ClearinghouseCase.facility_id==facility_id,ClearinghouseCase.idempotency_key==idempotency_key))
    if existing:return existing
    from app.billing.models import Invoice
    claim=db.get(Claim,claim_id) if claim_id else None
    invoice=db.get(Invoice,invoice_id) if invoice_id else (db.get(Invoice,claim.invoice_id) if claim else None)
    if invoice is None: raise ClearinghouseError("INVOICE_NOT_FOUND")
    if invoice.facility_id!=facility_id: raise ClearinghouseError("FACILITY_ACCESS_DENIED")
    payer_id=claim.payer_id if claim else invoice.payer_id
    patient_id=claim.patient_id if claim else invoice.patient_id
    amount=Decimal(str(claim.claim_amount)) if claim else Decimal(str(invoice.total_amount or invoice.payer_amount or 0))
    if amount<=0: raise ClearinghouseError("CLAIM_AMOUNT_INVALID")
    if claim is not None and claim.status not in {"READY","SUBMITTED","ACCEPTED","UNDER_REVIEW","PARTIALLY_PAID","PAID","REJECTED"}:
        raise ClearinghouseError("CLAIM_NOT_READY_FOR_CLEARINGHOUSE")
    payer=db.get(Payer,payer_id) if payer_id else None
    source=_source(payer,claim) if claim else "SELF_PAY"
    route=_route(db,facility_id,payer_id,source)
    case=ClearinghouseCase(case_number=_number(),facility_id=facility_id,claim_id=claim.id if claim else None,invoice_id=invoice.id,patient_id=patient_id,payer_id=payer_id,source_type=source,adapter_code=route.adapter_code if route else None,idempotency_key=idempotency_key,claim_amount=amount,approved_amount=Decimal(str(claim.approved_amount)) if claim else amount,paid_amount=Decimal(str(claim.paid_amount)) if claim else Decimal("0"),created_by=actor_id)
    db.add(case);db.flush();_event(db,case,"INTAKE_CREATED",actor_id,to_status="VALIDATING",metadata={"source_type":source,"adapter_code":case.adapter_code,"claim_linked":bool(claim)})
    record_audit(db,action="CLEARINGHOUSE_INTAKE",resource_type="CLEARINGHOUSE_CASE",resource_id=str(case.id),result="SUCCESS",user_id=actor_id,facility_id=facility_id,patient_id=case.patient_id,metadata={"case_number":case.case_number,"source_type":source,"claim_linked":bool(claim)},commit=False)
    db.commit();db.refresh(case);return case

def validate_case(db:Session,case_id:UUID,facility_id:UUID,actor_id:UUID|None=None)->list[str]:
    case=db.scalar(select(ClearinghouseCase).where(ClearinghouseCase.id==case_id).with_for_update())
    if case is None:raise ClearinghouseError("CASE_NOT_FOUND")
    if case.facility_id!=facility_id:raise ClearinghouseError("FACILITY_ACCESS_DENIED")
    errors=[]
    if case.status not in {"INTAKE","VALIDATING","FAILED","REJECTED"}: errors.append("CASE_NOT_VALIDATABLE")
    if case.claim_amount<=0: errors.append("CLAIM_AMOUNT_INVALID")
    if case.payer_id is None and case.source_type!="SELF_PAY":errors.append("PAYER_REQUIRED")
    route=_route(db,facility_id,case.payer_id,case.source_type)
    if route is None:errors.append("CLEARINGHOUSE_ROUTE_NOT_CONFIGURED")
    elif not route.active:errors.append("CLEARINGHOUSE_ROUTE_INACTIVE")
    case.status="FAILED" if errors else "READY"
    case.last_error=";".join(errors) if errors else None
    _event(db,case,"VALIDATION",actor_id,to_status=case.status,metadata={"errors":errors})
    db.commit();db.refresh(case);return errors

def queue_case(db:Session,case_id:UUID,facility_id:UUID,actor_id:UUID|None=None)->ClearinghouseCase:
    case=db.scalar(select(ClearinghouseCase).where(ClearinghouseCase.id==case_id).with_for_update())
    if case is None:raise ClearinghouseError("CASE_NOT_FOUND")
    if case.facility_id!=facility_id:raise ClearinghouseError("FACILITY_ACCESS_DENIED")
    if case.status=="QUEUED":return case
    if case.status!="READY":raise ClearinghouseError("CASE_NOT_READY")
    route=_route(db,facility_id,case.payer_id,case.source_type)
    if route is None or not route.supports_submission:raise ClearinghouseError("CLEARINGHOUSE_SUBMISSION_NOT_CONFIGURED")
    case.queued_at=datetime.now(timezone.utc);_event(db,case,"QUEUED",actor_id,to_status="QUEUED",metadata={"adapter_code":route.adapter_code})
    db.commit();db.refresh(case);return case

def submit_case(db:Session,case_id:UUID,facility_id:UUID,actor_id:UUID|None=None)->ClearinghouseCase:
    case=db.scalar(select(ClearinghouseCase).where(ClearinghouseCase.id==case_id).with_for_update())
    if case is None:raise ClearinghouseError("CASE_NOT_FOUND")
    if case.facility_id!=facility_id:raise ClearinghouseError("FACILITY_ACCESS_DENIED")
    if case.status not in {"READY","QUEUED","FAILED"}:raise ClearinghouseError("CASE_NOT_SUBMITTABLE")
    route=_route(db,facility_id,case.payer_id,case.source_type)
    if route is None or not route.supports_submission:raise ClearinghouseError("CLEARINGHOUSE_SUBMISSION_NOT_CONFIGURED")
    from app.claims.service import build_claim_submission_payload
    payload=build_claim_submission_payload(db,case.claim_id,facility_id) if case.claim_id else {"case_number":case.case_number}
    integration=db.scalar(select(Integration).where(Integration.facility_id==facility_id,Integration.status=="ACTIVE",Integration.integration_type.in_(["PAYER_CLAIMS","CLAIMS"]),Integration.provider==route.adapter_code).order_by(Integration.created_at.desc()).limit(1))
    if integration is None:raise ClearinghouseError("ADAPTER_INTEGRATION_NOT_CONFIGURED")
    txid=f"{case.case_number}:{case.attempt_count+1}"
    try:tx=queue_transaction(db,facility_id,integration.id,txid,"CLEARINGHOUSE",case.id,"OUTBOUND",case.case_number)
    except IntegrationError as exc:db.rollback();raise ClearinghouseError(str(exc)) from exc
    tx.response_data={"request":payload,"source_type":case.source_type,"adapter_code":route.adapter_code}
    case.attempt_count+=1;case.submitted_at=datetime.now(timezone.utc);case.last_error=None
    _event(db,case,"SUBMITTED",actor_id,to_status="SUBMITTED",metadata={"transaction_id":tx.transaction_id,"adapter_code":route.adapter_code})
    db.commit();db.refresh(case);return case

def receive_status(db:Session,case_id:UUID,facility_id:UUID,payload,actor_id:UUID|None=None)->ClearinghouseCase:
    case=db.scalar(select(ClearinghouseCase).where(ClearinghouseCase.id==case_id).with_for_update())
    if case is None:raise ClearinghouseError("CASE_NOT_FOUND")
    if case.facility_id!=facility_id:raise ClearinghouseError("FACILITY_ACCESS_DENIED")
    status=payload.status.strip().upper()
    aliases={"ACK":"ACKNOWLEDGED","PENDING":"IN_REVIEW","APPROVED":"ACCEPTED","PARTIAL":"PARTIALLY_PAID","DENIED":"REJECTED"}
    status=aliases.get(status,status)
    if status not in STATUSES:raise ClearinghouseError("INVALID_CLEARINGHOUSE_STATUS")
    if status in {"REJECTED"}:
        code=(payload.response_code or "OTHER").strip().upper()
        denial=db.scalar(select(ClearinghouseDenialCode).where(ClearinghouseDenialCode.code==code,ClearinghouseDenialCode.active.is_(True)))
        case.denial_code=code;case.denial_category=denial.category if denial else DENIALS.get(code,"OTHER");case.denial_message=payload.response_message
    if payload.external_reference:
        duplicate=db.scalar(select(ClearinghouseCase.id).where(ClearinghouseCase.external_reference==payload.external_reference, ClearinghouseCase.id!=case.id))
        if duplicate:raise ClearinghouseError("DUPLICATE_EXTERNAL_REFERENCE")
        case.external_reference=payload.external_reference
    if payload.approved_amount is not None:case.approved_amount=Decimal(str(payload.approved_amount)).quantize(Decimal("0.01"))
    if payload.paid_amount is not None:case.paid_amount=Decimal(str(payload.paid_amount)).quantize(Decimal("0.01"))
    if status in {"ACKNOWLEDGED","IN_REVIEW"}:case.acknowledged_at=case.acknowledged_at or datetime.now(timezone.utc)
    if status in {"ACCEPTED","PARTIALLY_PAID","PAID","RECONCILED","REJECTED"}:case.resolved_at=datetime.now(timezone.utc)
    _event(db,case,"PAYER_STATUS_RECEIVED",actor_id,to_status=status,metadata={"response_code":payload.response_code})
    db.commit();db.refresh(case);return case

def record_remittance(db:Session,case_id:UUID,facility_id:UUID,payload,actor_id:UUID|None=None)->ClearinghouseRemittance:
    case=db.scalar(select(ClearinghouseCase).where(ClearinghouseCase.id==case_id).with_for_update())
    if case is None:raise ClearinghouseError("CASE_NOT_FOUND")
    if case.facility_id!=facility_id:raise ClearinghouseError("FACILITY_ACCESS_DENIED")
    rem=ClearinghouseRemittance(case_id=case.id,external_reference=payload.external_reference,status=payload.status.strip().upper(),approved_amount=payload.approved_amount,paid_amount=payload.paid_amount,patient_amount=payload.patient_amount,currency=payload.currency.upper(),event_metadata=payload.metadata)
    db.add(rem);case.approved_amount=payload.approved_amount;case.paid_amount=payload.paid_amount
    target="PAID" if payload.paid_amount>0 and payload.paid_amount>=payload.approved_amount else ("PARTIALLY_PAID" if payload.paid_amount>0 else case.status)
    _event(db,case,"REMITTANCE_RECEIVED",actor_id,to_status=target,metadata={"paid_amount":str(payload.paid_amount)})
    db.commit();db.refresh(rem);return rem

def list_cases(db:Session,facility_id:UUID,limit:int=100,status:str|None=None):
    q=select(ClearinghouseCase).where(ClearinghouseCase.facility_id==facility_id)
    if status:q=q.where(ClearinghouseCase.status==status.upper())
    return list(db.scalars(q.order_by(ClearinghouseCase.updated_at.desc()).limit(limit)).all())

def events(db:Session,case_id:UUID,facility_id:UUID):
    case=db.get(ClearinghouseCase,case_id)
    if case is None:raise ClearinghouseError("CASE_NOT_FOUND")
    if case.facility_id!=facility_id:raise ClearinghouseError("FACILITY_ACCESS_DENIED")
    return list(db.scalars(select(ClearinghouseEvent).where(ClearinghouseEvent.case_id==case_id).order_by(ClearinghouseEvent.created_at.asc())).all())

def overview(db:Session,facility_id:UUID):
    counts={}
    for status,count in db.execute(select(ClearinghouseCase.status,func.count(ClearinghouseCase.id)).where(ClearinghouseCase.facility_id==facility_id).group_by(ClearinghouseCase.status)):
        counts[status]=count
    totals=db.execute(select(func.coalesce(func.sum(ClearinghouseCase.claim_amount),0),func.coalesce(func.sum(ClearinghouseCase.approved_amount),0),func.coalesce(func.sum(ClearinghouseCase.paid_amount),0)).where(ClearinghouseCase.facility_id==facility_id)).one()
    return {"cases":sum(counts.values()),"by_status":counts,"claim_amount":float(totals[0]),"approved_amount":float(totals[1]),"paid_amount":float(totals[2]),"sources":SOURCE_TYPES}

def seed_denial_codes(db:Session):
    defaults=[
      ("AUTHORIZATION","AUTHORIZATION","Authorization required","Missing or invalid preauthorization.","Obtain or correct preauthorization before resubmission."),
      ("ELIGIBILITY","ELIGIBILITY","Eligibility failure","Coverage was inactive, invalid or not established.","Re-verify coverage and correct member details."),
      ("DOCUMENTATION","DOCUMENTATION","Documentation incomplete","Required supporting documents were missing.","Attach the required clinical or billing documentation."),
      ("DUPLICATE","DUPLICATE","Duplicate claim","Payer identified a duplicate submission.","Check prior submissions and external reference."),
      ("CODING","CODING","Coding or classification error","Service or diagnosis coding was rejected.","Review coding and resubmit corrected data."),
      ("TARIFF","TARIFF","Tariff or pricing mismatch","Submitted tariff differs from contracted or allowed tariff.","Recalculate against the active benefit/tariff rule."),
      ("TIMING","TIMING","Submission timing","Claim was submitted outside the permitted window.","Review service and submission dates and payer rules."),
      ("CLINICAL","CLINICAL","Clinical review","Payer requires additional clinical review.","Provide the requested clinical evidence."),
      ("TECHNICAL","TECHNICAL","Technical rejection","Payer interface rejected the transaction.","Inspect adapter response and retry safely."),
      ("OTHER","OTHER","Other rejection","Unclassified payer rejection.","Review payer response and route to the appropriate owner.")
    ]
    for code,cat,title,desc,fix in defaults:
        if db.scalar(select(ClearinghouseDenialCode.id).where(ClearinghouseDenialCode.code==code)) is None:db.add(ClearinghouseDenialCode(code=code,category=cat,title=title,description=desc,recommended_action=fix))
    db.commit()
