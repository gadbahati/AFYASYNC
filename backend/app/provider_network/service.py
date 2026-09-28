from datetime import datetime, timezone
from uuid import UUID
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from app.audit.service import record_audit
from app.facilities.models import Facility
from app.provider_network.models import ProviderNetworkMembership, ProviderNetworkService, ProviderNetworkContract

class ProviderNetworkError(ValueError): pass

def _facility(db, facility_id):
    f=db.get(Facility,facility_id)
    if not f: raise ProviderNetworkError("FACILITY_NOT_FOUND")
    return f

def add_membership(db, payload, actor):
    f=_facility(db,payload["facility_id"])
    if f.status!="ACTIVE": raise ProviderNetworkError("FACILITY_NOT_ACTIVE")
    row=db.scalar(select(ProviderNetworkMembership).where(ProviderNetworkMembership.facility_id==f.id,ProviderNetworkMembership.network_code==payload["network_code"]))
    if row: raise ProviderNetworkError("MEMBERSHIP_EXISTS")
    row=ProviderNetworkMembership(**payload,participation_status="PENDING")
    db.add(row); db.flush()
    record_audit(db,action="CREATE_PROVIDER_NETWORK_MEMBERSHIP",resource_type="PROVIDER_NETWORK",resource_id=str(row.id),result="SUCCESS",user_id=actor,facility_id=f.id,metadata={"network_code":row.network_code},commit=False)
    db.commit(); db.refresh(row); return row

def list_memberships(db, network_code=None, facility_id=None, status=None, limit=100):
    q=select(ProviderNetworkMembership).order_by(ProviderNetworkMembership.created_at.desc())
    if network_code: q=q.where(ProviderNetworkMembership.network_code==network_code)
    if facility_id: q=q.where(ProviderNetworkMembership.facility_id==facility_id)
    if status: q=q.where(ProviderNetworkMembership.participation_status==status)
    return list(db.scalars(q.limit(min(max(limit,1),200))))

def set_membership_status(db, membership_id, status, actor):
    row=db.get(ProviderNetworkMembership,membership_id)
    if not row: raise ProviderNetworkError("MEMBERSHIP_NOT_FOUND")
    allowed={"PENDING","ACTIVE","SUSPENDED","TERMINATED"}
    if status not in allowed: raise ProviderNetworkError("INVALID_MEMBERSHIP_STATUS")
    row.participation_status=status
    if status=="ACTIVE" and row.effective_from is None: row.effective_from=datetime.now(timezone.utc)
    if status=="TERMINATED" and row.effective_to is None: row.effective_to=datetime.now(timezone.utc)
    record_audit(db,action="UPDATE_PROVIDER_NETWORK_MEMBERSHIP",resource_type="PROVIDER_NETWORK",resource_id=str(row.id),result="SUCCESS",user_id=actor,facility_id=row.facility_id,metadata={"status":status},commit=False)
    db.commit(); db.refresh(row); return row

def add_service(db,payload,actor):
    _facility(db,payload["facility_id"])
    row=db.scalar(select(ProviderNetworkService).where(ProviderNetworkService.facility_id==payload["facility_id"],ProviderNetworkService.network_code==payload["network_code"],ProviderNetworkService.service_code==payload["service_code"]))
    if row: raise ProviderNetworkError("SERVICE_EXISTS")
    row=ProviderNetworkService(**payload); db.add(row); db.flush()
    record_audit(db,action="CREATE_PROVIDER_NETWORK_SERVICE",resource_type="PROVIDER_NETWORK",resource_id=str(row.id),result="SUCCESS",user_id=actor,facility_id=row.facility_id,metadata={"service_code":row.service_code},commit=False)
    db.commit(); db.refresh(row); return row

def list_services(db,network_code=None,facility_id=None,service_code=None,limit=200):
    q=select(ProviderNetworkService).where(ProviderNetworkService.status=="ACTIVE").order_by(ProviderNetworkService.service_name)
    if network_code:q=q.where(ProviderNetworkService.network_code==network_code)
    if facility_id:q=q.where(ProviderNetworkService.facility_id==facility_id)
    if service_code:q=q.where(ProviderNetworkService.service_code==service_code)
    return list(db.scalars(q.limit(min(max(limit,1),500))))

def add_contract(db,payload,actor):
    _facility(db,payload["facility_id"])
    row=db.scalar(select(ProviderNetworkContract).where(ProviderNetworkContract.contract_reference==payload["contract_reference"]))
    if row: raise ProviderNetworkError("CONTRACT_EXISTS")
    row=ProviderNetworkContract(**payload,status="DRAFT");db.add(row);db.flush()
    record_audit(db,action="CREATE_PROVIDER_NETWORK_CONTRACT",resource_type="PROVIDER_NETWORK",resource_id=str(row.id),result="SUCCESS",user_id=actor,facility_id=row.facility_id,metadata={"contract_reference":row.contract_reference},commit=False)
    db.commit();db.refresh(row);return row

def set_contract_status(db,contract_id,status,actor):
    row=db.get(ProviderNetworkContract,contract_id)
    if not row: raise ProviderNetworkError("CONTRACT_NOT_FOUND")
    if status not in {"DRAFT","ACTIVE","SUSPENDED","EXPIRED","TERMINATED"}:raise ProviderNetworkError("INVALID_CONTRACT_STATUS")
    row.status=status
    record_audit(db,action="UPDATE_PROVIDER_NETWORK_CONTRACT",resource_type="PROVIDER_NETWORK",resource_id=str(row.id),result="SUCCESS",user_id=actor,facility_id=row.facility_id,metadata={"status":status},commit=False)
    db.commit();db.refresh(row);return row

def overview(db):
    memberships=db.scalar(select(func.count()).select_from(ProviderNetworkMembership)) or 0
    active=db.scalar(select(func.count()).select_from(ProviderNetworkMembership).where(ProviderNetworkMembership.participation_status=="ACTIVE")) or 0
    services=db.scalar(select(func.count()).select_from(ProviderNetworkService).where(ProviderNetworkService.status=="ACTIVE")) or 0
    contracts=db.scalar(select(func.count()).select_from(ProviderNetworkContract)) or 0
    active_contracts=db.scalar(select(func.count()).select_from(ProviderNetworkContract).where(ProviderNetworkContract.status=="ACTIVE")) or 0
    networks=list(db.scalars(select(ProviderNetworkMembership.network_code,ProviderNetworkMembership.network_name).distinct().order_by(ProviderNetworkMembership.network_code)))
    return {"memberships":memberships,"active_memberships":active,"services":services,"contracts":contracts,"active_contracts":active_contracts,"networks":[{"network_code":n[0],"network_name":n[1]} for n in networks]}
