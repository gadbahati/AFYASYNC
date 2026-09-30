from datetime import datetime,timezone
from uuid import UUID
from sqlalchemy.orm import Session
from app.audit.service import record_audit
from app.national_capacity.service import search_service_capacity
def route(db:Session,*,actor_user_id:UUID,service_code:str,county:str|None=None,network_code:str|None=None,day:str|None=None,limit:int=20):
 try: target=datetime.fromisoformat(day).replace(tzinfo=timezone.utc) if day else datetime.now(timezone.utc)
 except ValueError as exc: raise ValueError("INVALID_DAY") from exc
 rows=search_service_capacity(db,actor_user_id=actor_user_id,service_code=service_code,network_code=network_code,county=county,day=target,limit=200)
 available=[r for r in rows if r["remaining"]>0]
 # Deterministic routing order: available capacity first, then shortest queue proxy
 available.sort(key=lambda r:(-r["remaining"],r["booked"],r["facility_name"].lower()))
 options=[]
 for r in available[:limit]:
  reasons=["ACTIVE_PROVIDER_NETWORK","SERVICE_AVAILABLE"]
  if r["referral_required"]: reasons.append("REFERRAL_REQUIRED")
  if county and r["county"] and r["county"].lower()==county.lower(): reasons.append("COUNTY_MATCH")
  options.append({**r,"route_reason":reasons})
 record_audit(db,action="GENERATE_REFERRAL_ROUTING_OPTIONS",resource_type="REFERRAL_ROUTING",result="SUCCESS",user_id=actor_user_id,metadata={"service_code":service_code,"county":county,"network_code":network_code,"date":target.date().isoformat(),"option_count":len(options)},commit=True)
 return {"service_code":service_code,"date":target.date().isoformat(),"options":options}
