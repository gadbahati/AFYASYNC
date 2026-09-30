from fastapi import APIRouter,Depends,HTTPException
from sqlalchemy.orm import Session
from app.auth.dependencies import require_national_permission
from app.database import get_db
from app.rbac.models import User
from app.referral_routing.schemas import RoutingRequest
from app.referral_routing.service import route
router=APIRouter(prefix="/api/v1/referral-routing",tags=["Referral Routing"])
@router.post("/options")
def options(body:RoutingRequest,user:User=Depends(require_national_permission("exchange.read")),db:Session=Depends(get_db)):
 try:return route(db,actor_user_id=user.id,service_code=body.service_code,county=body.county,network_code=body.network_code,day=body.day,limit=body.limit)
 except ValueError as exc: raise HTTPException(status_code=400,detail=str(exc)) from exc
