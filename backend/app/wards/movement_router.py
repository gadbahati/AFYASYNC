from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.auth.dependencies import get_db, require_permission
from app.wards.movement_service import transfer_patient

router = APIRouter(prefix="/api/v1/wards", tags=["Wards & Beds"])

class PatientTransfer(BaseModel):
    admission_id: UUID
    to_bed_id: UUID
    reason: str | None = None

@router.post("/transfer")
def transfer(payload: PatientTransfer, db: Session = Depends(get_db), user=Depends(require_permission("encounters.create"))):
    try:
        return transfer_patient(db, user.facility_id, user.id, payload.admission_id, payload.to_bed_id, payload.reason)
    except ValueError as exc:
        codes={"ADMISSION_NOT_FOUND":404,"BED_NOT_FOUND":404,"ADMISSION_NOT_ACTIVE":409,"BED_NOT_AVAILABLE":409}
        raise HTTPException(codes.get(str(exc),400), detail=str(exc))
