from uuid import UUID
from fastapi import APIRouter,Depends,HTTPException,Query
from sqlalchemy.orm import Session
from app.auth.dependencies import require_national_permission
from app.database import get_db
from app.health_exchange.schemas import ExchangeMessageCreate,ExchangeStatusUpdate
from app.health_exchange.service import *
from app.rbac.models import User
router=APIRouter(prefix="/api/v1/health-exchange",tags=["National Health Exchange"])
def ex(x):
    return HTTPException(status_code={"MESSAGE_ID_EXISTS":409,"MESSAGE_NOT_FOUND":404,"INVALID_STATUS":400}.get(str(x),400),detail=str(x))
@router.get("/overview")
def get_overview(_:User=Depends(require_national_permission("exchange.read")),db:Session=Depends(get_db)):return overview(db)
@router.get("/messages")
def get_messages(message_type:str|None=None,patient_id:UUID|None=None,status:str|None=None,limit:int=Query(100,ge=1,le=200),_:User=Depends(require_national_permission("exchange.read")),db:Session=Depends(get_db)):return list_messages(db,message_type,patient_id,status,limit)
@router.post("/messages",status_code=201)
def create_message(payload:ExchangeMessageCreate,user:User=Depends(require_national_permission("exchange.write")),db:Session=Depends(get_db)):
    try:return publish(db,payload.model_dump(),user.id)
    except HealthExchangeError as x:raise ex(x) from x
@router.patch("/messages/{message_id}/status")
def message_status(message_id:str,payload:ExchangeStatusUpdate,user:User=Depends(require_national_permission("exchange.write")),db:Session=Depends(get_db)):
    try:return update_status(db,message_id,payload.status,user.id)
    except HealthExchangeError as x:raise ex(x) from x
