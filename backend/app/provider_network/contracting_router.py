from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.auth.dependencies import require_national_permission
from app.database import get_db
from app.provider_network.schemas import MembershipVerificationUpdate, ContractAcceptance, ContractNegotiation, ContractRenewal, ContractEventOut
from app.provider_network.service import verify_membership, negotiate_contract, accept_contract, renew_contract, contract_events, contracting_overview, ProviderNetworkError
from app.rbac.models import User

router=APIRouter(prefix="/api/v1/provider-contracting",tags=["Provider Contracting & Empanelment"])

def fail(x):
    code=str(x)
    status={"MEMBERSHIP_NOT_FOUND":404,"CONTRACT_NOT_FOUND":404,"INVALID_VERIFICATION_TYPE":400,"INVALID_NEGOTIATION_STATE":409,"CONTRACT_NOT_READY_FOR_ACCEPTANCE":409,"ACTIVE_MEMBERSHIP_REQUIRED":409,"PROVIDER_VERIFICATION_INCOMPLETE":409,"INVALID_RENEWAL_STATE":409,"INVALID_RENEWAL_DATE":409}.get(code,400)
    return HTTPException(status_code=status,detail=code)

@router.get("/overview")
def overview(_:User=Depends(require_national_permission("facilities.network.read")),db:Session=Depends(get_db)):
    return contracting_overview(db)

@router.patch("/memberships/{membership_id}/verify")
def verify(membership_id:UUID,payload:MembershipVerificationUpdate,user:User=Depends(require_national_permission("facilities.network.manage")),db:Session=Depends(get_db)):
    try:return verify_membership(db,membership_id,payload.verification_type,payload.notes,user.id)
    except ProviderNetworkError as x:raise fail(x) from x

@router.post("/contracts/{contract_id}/negotiate")
def negotiate(contract_id:UUID,payload:ContractNegotiation,user:User=Depends(require_national_permission("facilities.network.manage")),db:Session=Depends(get_db)):
    try:return negotiate_contract(db,contract_id,user.id,payload.notes)
    except ProviderNetworkError as x:raise fail(x) from x

@router.post("/contracts/{contract_id}/accept")
def accept(contract_id:UUID,payload:ContractAcceptance,user:User=Depends(require_national_permission("facilities.network.manage")),db:Session=Depends(get_db)):
    try:return accept_contract(db,contract_id,user.id,payload.notes)
    except ProviderNetworkError as x:raise fail(x) from x

@router.post("/contracts/{contract_id}/renew")
def renew(contract_id:UUID,payload:ContractRenewal,user:User=Depends(require_national_permission("facilities.network.manage")),db:Session=Depends(get_db)):
    try:return renew_contract(db,contract_id,payload.effective_to,payload.renewal_due_at,user.id)
    except ProviderNetworkError as x:raise fail(x) from x

@router.get("/contracts/{contract_id}/events",response_model=list[ContractEventOut])
def events(contract_id:UUID,_:User=Depends(require_national_permission("facilities.network.read")),db:Session=Depends(get_db)):
    return contract_events(db,contract_id)
