from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.auth.dependencies import get_facility_context, require_permission
from app.claim_clearinghouse.schemas import RouteCreate, IntakeRequest, StatusUpdate, RemittanceRequest, CaseOut
from app.claim_clearinghouse.service import *
from app.database import get_db
from app.rbac.models import User

router=APIRouter(prefix="/api/v1/claims-clearinghouse",tags=["Universal Claims Clearinghouse"])

def err(x):
    code=str(x)
    mapping={"CASE_NOT_FOUND":404,"CLAIM_NOT_FOUND":404,"FACILITY_ACCESS_DENIED":403,"CLAIM_NOT_READY_FOR_CLEARINGHOUSE":409,"CASE_NOT_READY":409,"CASE_NOT_VALIDATABLE":409,"CLEARINGHOUSE_ROUTE_NOT_CONFIGURED":409,"CLEARINGHOUSE_SUBMISSION_NOT_CONFIGURED":409,"ADAPTER_INTEGRATION_NOT_CONFIGURED":409,"INVALID_CLEARINGHOUSE_STATUS":400,"DUPLICATE_EXTERNAL_REFERENCE":409}
    return HTTPException(status_code=mapping.get(code,400),detail=code)

@router.get("/overview")
def get_overview(db:Session=Depends(get_db),facility_id:UUID=Depends(get_facility_context),user:User=Depends(require_permission("reports.read"))):
    _=user;return overview(db,facility_id)

@router.get("/cases",response_model=list[CaseOut])
def cases(status:str|None=Query(default=None),limit:int=Query(default=100,ge=1,le=200),db:Session=Depends(get_db),facility_id:UUID=Depends(get_facility_context),user:User=Depends(require_permission("reports.read"))):
    _=user;return list_cases(db,facility_id,limit,status)

@router.post("/routes")
def create_route(payload:RouteCreate,db:Session=Depends(get_db),facility_id:UUID=Depends(get_facility_context),user:User=Depends(require_permission("claims.submit"))):
    route=ClearinghouseRoute(facility_id=facility_id,**payload.model_dump())
    db.add(route);db.commit();db.refresh(route);return route

@router.post("/intake",response_model=CaseOut,status_code=201)
def intake(payload:IntakeRequest,db:Session=Depends(get_db),facility_id:UUID=Depends(get_facility_context),user:User=Depends(require_permission("claims.create"))):
    try:return create_case(db,facility_id,payload.claim_id,payload.idempotency_key,user.id,payload.invoice_id)
    except ClearinghouseError as x:raise err(x) from x

@router.post("/cases/{case_id}/validate",response_model=CaseOut)
def validate(case_id:UUID,db:Session=Depends(get_db),facility_id:UUID=Depends(get_facility_context),user:User=Depends(require_permission("claims.validate"))):
    try:validate_case(db,case_id,facility_id,user.id);return db.get(ClearinghouseCase,case_id)
    except ClearinghouseError as x:raise err(x) from x

@router.post("/cases/{case_id}/queue",response_model=CaseOut)
def queue(case_id:UUID,db:Session=Depends(get_db),facility_id:UUID=Depends(get_facility_context),user:User=Depends(require_permission("claims.submit"))):
    try:return queue_case(db,case_id,facility_id,user.id)
    except ClearinghouseError as x:raise err(x) from x

@router.post("/cases/{case_id}/submit",response_model=CaseOut)
def submit(case_id:UUID,db:Session=Depends(get_db),facility_id:UUID=Depends(get_facility_context),user:User=Depends(require_permission("claims.submit"))):
    try:return submit_case(db,case_id,facility_id,user.id)
    except ClearinghouseError as x:raise err(x) from x

@router.post("/cases/{case_id}/status",response_model=CaseOut)
def status(case_id:UUID,payload:StatusUpdate,db:Session=Depends(get_db),facility_id:UUID=Depends(get_facility_context),user:User=Depends(require_permission("claims.validate"))):
    try:return receive_status(db,case_id,facility_id,payload,user.id)
    except ClearinghouseError as x:raise err(x) from x

@router.post("/cases/{case_id}/remittance",response_model=CaseOut)
def remittance(case_id:UUID,payload:RemittanceRequest,db:Session=Depends(get_db),facility_id:UUID=Depends(get_facility_context),user:User=Depends(require_permission("claims.reconcile"))):
    try:record_remittance(db,case_id,facility_id,payload,user.id);return db.get(ClearinghouseCase,case_id)
    except ClearinghouseError as x:raise err(x) from x

@router.get("/cases/{case_id}/events")
def case_events(case_id:UUID,db:Session=Depends(get_db),facility_id:UUID=Depends(get_facility_context),user:User=Depends(require_permission("reports.read"))):
    try:return events(db,case_id,facility_id)
    except ClearinghouseError as x:raise err(x) from x
