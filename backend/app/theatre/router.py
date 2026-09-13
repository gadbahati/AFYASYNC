from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.auth.dependencies import get_db, require_permission
from app.theatre.models import TheatreBooking, TheatreProcedure
from app.theatre.schemas import BookingCreate, BookingResponse, ProcedureCreate, ProcedureResponse, TheatreRecordCreate, TheatreRecordResponse
from app.theatre.service import book_procedure, complete_procedure, create_procedure

router = APIRouter(prefix="/api/v1/theatre", tags=["Theatre"])

def err(e):
    codes={"PATIENT_NOT_IN_FACILITY":403,"PROCEDURE_NOT_FOUND":404,"BOOKING_NOT_FOUND":404,"BOOKING_NOT_ACTIVE":409}
    return HTTPException(codes.get(str(e),400), detail=str(e))

@router.post("/procedures", response_model=ProcedureResponse, status_code=201)
def procedures(payload: ProcedureCreate, db: Session=Depends(get_db), user=Depends(require_permission("facilities.department.write"))): return create_procedure(db,user.facility_id,user.id,payload)

@router.get("/procedures", response_model=list[ProcedureResponse])
def list_procedures(db: Session=Depends(get_db), user=Depends(require_permission("patients.record.read"))): return db.scalars(select(TheatreProcedure).where(TheatreProcedure.facility_id==user.facility_id, TheatreProcedure.status=="ACTIVE").order_by(TheatreProcedure.name)).all()

@router.post("/bookings", response_model=BookingResponse, status_code=201)
def bookings(payload: BookingCreate, db: Session=Depends(get_db), user=Depends(require_permission("encounters.create"))):
    try: return book_procedure(db,user.facility_id,user.id,payload)
    except ValueError as e: raise err(e)

@router.get("/bookings", response_model=list[BookingResponse])
def list_bookings(db: Session=Depends(get_db), user=Depends(require_permission("patients.record.read"))): return db.scalars(select(TheatreBooking).where(TheatreBooking.facility_id==user.facility_id).order_by(TheatreBooking.scheduled_at.desc())).all()

@router.post("/bookings/{booking_id}/complete", response_model=TheatreRecordResponse)
def complete(booking_id: UUID, payload: TheatreRecordCreate, db: Session=Depends(get_db), user=Depends(require_permission("encounters.create"))):
    try: return complete_procedure(db,user.facility_id,user.id,booking_id,payload)
    except ValueError as e: raise err(e)
