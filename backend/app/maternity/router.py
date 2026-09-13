from uuid import UUID
from fastapi import APIRouter,Depends,HTTPException
from sqlalchemy.orm import Session
from app.auth.dependencies import get_db,require_permission
from app.maternity.schemas import *
from app.maternity.service import create_pregnancy,add_antenatal_visit,record_delivery,register_newborn
router=APIRouter(prefix="/api/v1/maternity",tags=["Maternity & ANC"])
def err(e):
    codes={"PATIENT_NOT_IN_FACILITY":403,"ACTIVE_PREGNANCY_EXISTS":409,"PREGNANCY_NOT_FOUND":404,"DELIVERY_NOT_FOUND":404}
    return HTTPException(codes.get(str(e),400),detail=str(e))
@router.post("/pregnancies",response_model=PregnancyResponse,status_code=201)
def pregnancy(p:PregnancyCreate,db:Session=Depends(get_db),u=Depends(require_permission("encounters.create"))):
    try:return create_pregnancy(db,u.facility_id,u.id,p)
    except ValueError as e:raise err(e)
@router.post("/pregnancies/{pregnancy_id}/visits",response_model=AntenatalVisitResponse,status_code=201)
def visit(pregnancy_id:UUID,p:AntenatalVisitCreate,db:Session=Depends(get_db),u=Depends(require_permission("encounters.create"))):
    try:return add_antenatal_visit(db,u.facility_id,u.id,pregnancy_id,p)
    except ValueError as e:raise err(e)
@router.post("/pregnancies/{pregnancy_id}/delivery",response_model=DeliveryResponse,status_code=201)
def delivery(pregnancy_id:UUID,p:DeliveryCreate,db:Session=Depends(get_db),u=Depends(require_permission("encounters.create"))):
    try:return record_delivery(db,u.facility_id,u.id,pregnancy_id,p)
    except ValueError as e:raise err(e)
@router.post("/deliveries/{delivery_id}/newborn",response_model=NewbornResponse,status_code=201)
def newborn(delivery_id:UUID,p:NewbornCreate,db:Session=Depends(get_db),u=Depends(require_permission("patients.create"))):
    try:return register_newborn(db,u.facility_id,u.id,delivery_id,p)
    except ValueError as e:raise err(e)
