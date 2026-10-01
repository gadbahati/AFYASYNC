from datetime import datetime, timezone
from uuid import UUID
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from app.audit.service import record_audit
from app.facilities.models import Facility
from app.provider_network.models import ProviderNetworkMembership, ProviderNetworkService, ProviderNetworkContract, ProviderContractEvent

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


def verify_membership(db, membership_id, verification_type, notes, actor):
    row=db.get(ProviderNetworkMembership,membership_id)
    if not row: raise ProviderNetworkError("MEMBERSHIP_NOT_FOUND")
    now=datetime.now(timezone.utc)
    if verification_type=="LICENSE": row.license_verified_at=now
    elif verification_type=="CREDENTIAL": row.credential_verified_at=now
    elif verification_type=="SERVICE": row.service_verified_at=now
    else: raise ProviderNetworkError("INVALID_VERIFICATION_TYPE")
    row.verification_notes=notes
    if row.license_verified_at and row.credential_verified_at and row.service_verified_at:
        row.credential_status="VERIFIED"
    record_audit(db,action="VERIFY_PROVIDER_NETWORK_MEMBERSHIP",resource_type="PROVIDER_NETWORK",resource_id=str(row.id),result="SUCCESS",user_id=actor,facility_id=row.facility_id,metadata={"verification_type":verification_type},commit=False)
    db.commit(); db.refresh(row); return row

def _contract_event(db, row, event_type, actor, from_status=None, to_status=None, notes=None, metadata=None):
    db.add(ProviderContractEvent(contract_id=row.id,event_type=event_type,from_status=from_status,to_status=to_status,actor_id=actor,notes=notes,metadata=metadata))

def negotiate_contract(db, contract_id, actor, notes=None):
    row=db.get(ProviderNetworkContract,contract_id)
    if not row: raise ProviderNetworkError("CONTRACT_NOT_FOUND")
    if row.status not in {"DRAFT","NEGOTIATING"}: raise ProviderNetworkError("INVALID_NEGOTIATION_STATE")
    old=row.status
    row.status="NEGOTIATING"
    row.tariff_negotiated_at=datetime.now(timezone.utc)
    _contract_event(db,row,"TARIFF_NEGOTIATED",actor,old,row.status,notes)
    db.commit(); db.refresh(row); return row

def accept_contract(db, contract_id, actor, notes=None):
    row=db.get(ProviderNetworkContract,contract_id)
    if not row: raise ProviderNetworkError("CONTRACT_NOT_FOUND")
    if row.status!="NEGOTIATING": raise ProviderNetworkError("CONTRACT_NOT_READY_FOR_ACCEPTANCE")
    membership=db.scalar(select(ProviderNetworkMembership).where(ProviderNetworkMembership.facility_id==row.facility_id,ProviderNetworkMembership.network_code==row.network_code))
    if not membership or membership.participation_status!="ACTIVE": raise ProviderNetworkError("ACTIVE_MEMBERSHIP_REQUIRED")
    if membership.credential_status!="VERIFIED" or not (membership.license_verified_at and membership.credential_verified_at and membership.service_verified_at):
        raise ProviderNetworkError("PROVIDER_VERIFICATION_INCOMPLETE")
    now=datetime.now(timezone.utc)
    old=row.status; row.status="ACTIVE"; row.accepted_at=now; row.accepted_by=actor
    if row.effective_from is None: row.effective_from=now
    _contract_event(db,row,"CONTRACT_ACCEPTED",actor,old,row.status,notes)
    record_audit(db,action="ACCEPT_PROVIDER_CONTRACT",resource_type="PROVIDER_NETWORK_CONTRACT",resource_id=str(row.id),result="SUCCESS",user_id=actor,facility_id=row.facility_id,metadata={"contract_reference":row.contract_reference},commit=False)
    db.commit(); db.refresh(row); return row

def renew_contract(db, contract_id, effective_to, renewal_due_at, actor):
    row=db.get(ProviderNetworkContract,contract_id)
    if not row: raise ProviderNetworkError("CONTRACT_NOT_FOUND")
    if row.status not in {"ACTIVE","EXPIRED"}: raise ProviderNetworkError("INVALID_RENEWAL_STATE")
    if effective_to <= datetime.now(timezone.utc): raise ProviderNetworkError("INVALID_RENEWAL_DATE")
    row.effective_to=effective_to
    row.renewal_due_at=renewal_due_at
    old=row.status; row.status="ACTIVE"
    _contract_event(db,row,"CONTRACT_RENEWED",actor,old,row.status,metadata={"renewal_due_at":renewal_due_at.isoformat() if renewal_due_at else None})
    db.commit(); db.refresh(row); return row

def contract_events(db, contract_id, limit=100):
    return list(db.scalars(select(ProviderContractEvent).where(ProviderContractEvent.contract_id==contract_id).order_by(ProviderContractEvent.created_at.desc()).limit(min(max(limit,1),200))))

def contracting_overview(db):
    now=datetime.now(timezone.utc)
    expiring=db.scalar(select(func.count()).select_from(ProviderNetworkContract).where(ProviderNetworkContract.status=="ACTIVE",ProviderNetworkContract.renewal_due_at!=None,ProviderNetworkContract.renewal_due_at<=now)) or 0
    pending_verification=db.scalar(select(func.count()).select_from(ProviderNetworkMembership).where(ProviderNetworkMembership.credential_status!="VERIFIED")) or 0
    negotiating=db.scalar(select(func.count()).select_from(ProviderNetworkContract).where(ProviderNetworkContract.status=="NEGOTIATING")) or 0
    return {"pending_verification":pending_verification,"negotiating_contracts":negotiating,"renewals_due":expiring}
