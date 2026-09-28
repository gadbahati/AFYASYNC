from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.auth.dependencies import get_facility_context, require_permission
from app.database import get_db
from app.financing_preauthorization.schemas import FinancingPreauthRequest, FinancingPreauthDecision, FinancingPreauthResponse
from app.financing_preauthorization.service import FinancingPreauthError, request, decide

router=APIRouter(prefix="/api/v1/financing-preauthorizations",tags=["Financing preauthorizations"])

@router.post("",response_model=FinancingPreauthResponse,status_code=201)
def create(payload:FinancingPreauthRequest,db:Session=Depends(get_db),facility_id:UUID=Depends(get_facility_context),user=Depends(require_permission("encounters.create"))):
    try: return request(db,facility_id=facility_id,actor_user_id=user.id,payload=payload)
    except FinancingPreauthError as exc: raise HTTPException(status_code=409,detail=str(exc)) from exc

@router.post("/{authorization_id}/decision",response_model=FinancingPreauthResponse)
def decision(authorization_id:UUID,payload:FinancingPreauthDecision,db:Session=Depends(get_db),facility_id:UUID=Depends(get_facility_context),user=Depends(require_permission("encounters.create"))):
    try: return decide(db,authorization_id=authorization_id,facility_id=facility_id,actor_user_id=user.id,payload=payload)
    except FinancingPreauthError as exc: raise HTTPException(status_code=409,detail=str(exc)) from exc
