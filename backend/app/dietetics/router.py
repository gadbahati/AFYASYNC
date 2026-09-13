from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.auth.dependencies import get_db, require_permission
from app.dietetics.schemas import NutritionAssessmentCreate, NutritionAssessmentResponse, DietOrderCreate, DietOrderResponse
from app.dietetics.service import assess_nutrition, order_diet
router=APIRouter(prefix="/api/v1/dietetics",tags=["Dietetics"])
def error(e): return HTTPException(403 if str(e)=="PATIENT_NOT_IN_FACILITY" else 400,detail=str(e))
@router.post("/assessments",response_model=NutritionAssessmentResponse,status_code=201)
def assessment(p:NutritionAssessmentCreate,db:Session=Depends(get_db),u=Depends(require_permission("encounters.create"))):
 try:return assess_nutrition(db,u.facility_id,u.id,p)
 except ValueError as e:raise error(e)
@router.post("/orders",response_model=DietOrderResponse,status_code=201)
def diet_order(p:DietOrderCreate,db:Session=Depends(get_db),u=Depends(require_permission("encounters.create"))):
 try:return order_diet(db,u.facility_id,u.id,p)
 except ValueError as e:raise error(e)
