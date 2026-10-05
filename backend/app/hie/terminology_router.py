"""Terminology APIs for national-code lookup and cross-system mapping."""
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from app.auth.dependencies import get_facility_context, require_permission
from app.database import get_db
from app.hie.terminology_service import search_concepts, validate_code, map_code, upsert_concept, upsert_mapping
from app.rbac.models import User

router=APIRouter(prefix="/api/v1/terminology",tags=["Terminology"])

class ConceptBody(BaseModel):
    system: str=Field(min_length=1,max_length=500)
    version: str|None=Field(default=None,max_length=80)
    code: str=Field(min_length=1,max_length=200)
    display: str=Field(min_length=1,max_length=500)
    definition: str|None=None
    status: str=Field(default="ACTIVE",max_length=30)
    properties: dict=Field(default_factory=dict)
    source: str=Field(default="AFYASYNC",max_length=100)

class MappingBody(BaseModel):
    source_system: str=Field(min_length=1,max_length=500)
    source_code: str=Field(min_length=1,max_length=200)
    target_system: str=Field(min_length=1,max_length=500)
    target_code: str=Field(min_length=1,max_length=200)
    equivalence: str=Field(default="equivalent",max_length=30)
    source_display: str|None=None
    target_display: str|None=None
    status: str=Field(default="ACTIVE",max_length=30)
    provenance: dict=Field(default_factory=dict)

@router.get("/lookup")
def lookup(system: str|None=None, code: str|None=None, text: str|None=None, limit: int=Query(50,ge=1,le=200), db: Session=Depends(get_db), facility_id: UUID=Depends(get_facility_context), user: User=Depends(require_permission("reports.read"))):
    _=facility_id,user
    return [{"id":str(x.id),"system":x.system,"version":x.version,"code":x.code,"display":x.display,"definition":x.definition,"properties":x.properties,"source":x.source} for x in search_concepts(db,system,code,text,limit)]

@router.get("/validate")
def validate(system: str, code: str, version: str|None=None, db: Session=Depends(get_db), facility_id: UUID=Depends(get_facility_context), user: User=Depends(require_permission("reports.read"))):
    _=facility_id,user
    row=validate_code(db,system,code,version)
    return {"valid":row is not None,"concept": {"system":row.system,"version":row.version,"code":row.code,"display":row.display} if row else None}

@router.get("/map")
def mapping(source_system: str, source_code: str, target_system: str, db: Session=Depends(get_db), facility_id: UUID=Depends(get_facility_context), user: User=Depends(require_permission("reports.read"))):
    _=facility_id,user
    return [{"source_system":x.source_system,"source_code":x.source_code,"target_system":x.target_system,"target_code":x.target_code,"equivalence":x.equivalence,"source_display":x.source_display,"target_display":x.target_display,"provenance":x.provenance} for x in map_code(db,source_system,source_code,target_system)]

@router.put("/concepts")
def put_concept(body: ConceptBody, db: Session=Depends(get_db), facility_id: UUID=Depends(get_facility_context), user: User=Depends(require_permission("reports.read"))):
    _=facility_id
    row=upsert_concept(db,data=body.model_dump(),actor_user_id=user.id); db.commit()
    return {"id":str(row.id),"system":row.system,"version":row.version,"code":row.code,"display":row.display,"status":row.status}

@router.put("/mappings")
def put_mapping(body: MappingBody, db: Session=Depends(get_db), facility_id: UUID=Depends(get_facility_context), user: User=Depends(require_permission("reports.read"))):
    _=facility_id
    try:
        row=upsert_mapping(db,data=body.model_dump(),actor_user_id=user.id)
        db.commit()
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {"id":str(row.id),"source_system":row.source_system,"source_code":row.source_code,"target_system":row.target_system,"target_code":row.target_code,"equivalence":row.equivalence,"status":row.status}
