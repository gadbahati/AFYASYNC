from uuid import UUID
from fastapi import APIRouter,Depends,HTTPException,Query
from sqlalchemy.orm import Session
from app.auth.dependencies import require_national_permission
from app.database import get_db
from app.provider_network.schemas import MembershipCreate,MembershipStatusUpdate,ServiceCreate,ContractCreate,ContractStatusUpdate
from app.provider_network.service import *
from app.rbac.models import User

router=APIRouter(prefix="/api/v1/provider-network",tags=["Provider Network"])
def e(x):
    return HTTPException(status_code={"FACILITY_NOT_FOUND":404,"MEMBERSHIP_NOT_FOUND":404,"CONTRACT_NOT_FOUND":404,"MEMBERSHIP_EXISTS":409,"SERVICE_EXISTS":409,"CONTRACT_EXISTS":409,"FACILITY_NOT_ACTIVE":409}.get(str(x),400),detail=str(x))
@router.get("/overview")
def get_overview(_:User=Depends(require_national_permission("facilities.network.read")),db:Session=Depends(get_db)):return overview(db)
@router.get("/memberships")
def get_memberships(network_code:str|None=None,facility_id:UUID|None=None,status:str|None=None,limit:int=Query(100,ge=1,le=200),_:User=Depends(require_national_permission("facilities.network.read")),db:Session=Depends(get_db)):return list_memberships(db,network_code,facility_id,status,limit)
@router.post("/memberships",status_code=201)
def create_membership(payload:MembershipCreate,user:User=Depends(require_national_permission("facilities.network.manage")),db:Session=Depends(get_db)):
    try:return add_membership(db,payload.model_dump(),user.id)
    except ProviderNetworkError as x:raise e(x) from x
@router.patch("/memberships/{membership_id}/status")
def membership_status(membership_id:UUID,payload:MembershipStatusUpdate,user:User=Depends(require_national_permission("facilities.network.manage")),db:Session=Depends(get_db)):
    try:return set_membership_status(db,membership_id,payload.status,user.id)
    except ProviderNetworkError as x:raise e(x) from x
@router.get("/services")
def get_services(network_code:str|None=None,facility_id:UUID|None=None,service_code:str|None=None,limit:int=Query(200,ge=1,le=500),_:User=Depends(require_national_permission("facilities.network.read")),db:Session=Depends(get_db)):return list_services(db,network_code,facility_id,service_code,limit)
@router.post("/services",status_code=201)
def create_service(payload:ServiceCreate,user:User=Depends(require_national_permission("facilities.network.manage")),db:Session=Depends(get_db)):
    try:return add_service(db,payload.model_dump(),user.id)
    except ProviderNetworkError as x:raise e(x) from x
@router.get("/contracts")
def get_contracts(network_code:str|None=None,facility_id:UUID|None=None,limit:int=Query(100,ge=1,le=200),_:User=Depends(require_national_permission("facilities.network.read")),db:Session=Depends(get_db)):return list(db.scalars(select(ProviderNetworkContract).where(*( [ProviderNetworkContract.network_code==network_code] if network_code else []), *([ProviderNetworkContract.facility_id==facility_id] if facility_id else [])).order_by(ProviderNetworkContract.created_at.desc()).limit(limit)))
@router.post("/contracts",status_code=201)
def create_contract(payload:ContractCreate,user:User=Depends(require_national_permission("facilities.network.manage")),db:Session=Depends(get_db)):
    try:return add_contract(db,payload.model_dump(),user.id)
    except ProviderNetworkError as x:raise e(x) from x
@router.patch("/contracts/{contract_id}/status")
def contract_status(contract_id:UUID,payload:ContractStatusUpdate,user:User=Depends(require_national_permission("facilities.network.manage")),db:Session=Depends(get_db)):
    try:return set_contract_status(db,contract_id,payload.status,user.id)
    except ProviderNetworkError as x:raise e(x) from x
