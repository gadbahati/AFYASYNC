from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.auth.dependencies import get_db, require_permission
from app.wards.models import Bed, Ward
from app.wards.schemas import BedAssign, BedCreate, BedResponse, BedAssignmentResponse, WardCreate, WardResponse
from app.wards.service import assign_bed, create_bed, create_ward, release_bed

router = APIRouter(prefix="/api/v1/wards", tags=["Wards & Beds"])

def err(e):
    codes = {"WARD_NOT_FOUND":404,"BED_NOT_FOUND":404,"ADMISSION_NOT_FOUND":404,"ADMISSION_NOT_ACTIVE":409,"BED_NOT_AVAILABLE":409,"BED_NOT_OCCUPIED":409}
    return HTTPException(codes.get(str(e),400), detail=str(e))

@router.post("", response_model=WardResponse, status_code=201)
def ward(payload: WardCreate, db: Session = Depends(get_db), user=Depends(require_permission("facilities.department.write"))):
    return create_ward(db, user.facility_id, user.id, payload.name, payload.ward_type)

@router.get("", response_model=list[WardResponse])
def wards(db: Session = Depends(get_db), user=Depends(require_permission("patients.record.read"))):
    return db.scalars(select(Ward).where(Ward.facility_id == user.facility_id, Ward.status == "ACTIVE").order_by(Ward.name)).all()

@router.post("/beds", response_model=BedResponse, status_code=201)
def bed(payload: BedCreate, db: Session = Depends(get_db), user=Depends(require_permission("facilities.department.write"))):
    try: return create_bed(db, user.facility_id, user.id, payload.ward_id, payload.bed_number)
    except ValueError as e: raise err(e)

@router.get("/{ward_id}/beds", response_model=list[BedResponse])
def beds(ward_id: UUID, db: Session = Depends(get_db), user=Depends(require_permission("patients.record.read"))):
    ward = db.scalar(select(Ward).where(Ward.id == ward_id, Ward.facility_id == user.facility_id))
    if not ward: raise HTTPException(404, "Ward not found")
    return db.scalars(select(Bed).where(Bed.ward_id == ward_id).order_by(Bed.bed_number)).all()

@router.post("/beds/{bed_id}/assign", response_model=BedAssignmentResponse)
def assign(bed_id: UUID, payload: BedAssign, db: Session = Depends(get_db), user=Depends(require_permission("encounters.create"))):
    try: return assign_bed(db, user.facility_id, user.id, bed_id, payload.admission_id)
    except ValueError as e: raise err(e)

@router.post("/beds/{bed_id}/release", response_model=BedAssignmentResponse)
def release(bed_id: UUID, db: Session = Depends(get_db), user=Depends(require_permission("encounters.create"))):
    try: return release_bed(db, user.facility_id, user.id, bed_id)
    except ValueError as e: raise err(e)
