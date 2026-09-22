"""Clinical Safety Engine API."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth.dependencies import get_facility_context, require_permission
from app.clinical_safety.engine import run_clinical_safety_check
from app.clinical_safety.models import MedicationSafetyFlag
from app.database import get_db
from app.pharmacy.safety_schemas import SafetyCheckResponse
from app.rbac.models import User

router = APIRouter(prefix="/api/v1/clinical-safety", tags=["Clinical Safety"])

PHARMACY_READ = "pharmacy.read"
PHARMACY_WRITE = "pharmacy.write"


class ClinicalSafetyRequest(BaseModel):
    patient_id: UUID
    encounter_id: UUID | None = None
    medication_ids: list[UUID] = Field(min_length=1, max_length=30)
    patient_is_pregnant: bool | None = None


class SafetyFlagUpsert(BaseModel):
    medication_id: UUID
    high_risk: bool = False
    black_box: bool = False
    pregnancy_category: str | None = Field(default=None, max_length=10)
    paediatric_caution: bool = False
    renal_caution: bool = False
    notes: str | None = Field(default=None, max_length=2000)


@router.post("/check", response_model=SafetyCheckResponse)
def clinical_safety_check(
    payload: ClinicalSafetyRequest,
    db: Session = Depends(get_db),
    facility_id: UUID = Depends(get_facility_context),
    user: User = Depends(require_permission(PHARMACY_READ)),
) -> SafetyCheckResponse:
    result = run_clinical_safety_check(
        db,
        patient_id=payload.patient_id,
        facility_id=facility_id,
        medication_ids=payload.medication_ids,
        encounter_id=payload.encounter_id,
        patient_is_pregnant=payload.patient_is_pregnant,
        actor_user_id=user.id,
    )
    db.commit()
    return result


@router.put("/flags")
def upsert_safety_flag(
    payload: SafetyFlagUpsert,
    db: Session = Depends(get_db),
    facility_id: UUID = Depends(get_facility_context),
    user: User = Depends(require_permission(PHARMACY_WRITE)),
):
    _ = facility_id
    row = db.scalar(
        __import__("sqlalchemy").select(MedicationSafetyFlag).where(
            MedicationSafetyFlag.medication_id == payload.medication_id
        )
    )
    from sqlalchemy import select

    row = db.scalar(
        select(MedicationSafetyFlag).where(
            MedicationSafetyFlag.medication_id == payload.medication_id
        )
    )
    if row is None:
        row = MedicationSafetyFlag(medication_id=payload.medication_id)
        db.add(row)
    row.high_risk = payload.high_risk
    row.black_box = payload.black_box
    row.pregnancy_category = payload.pregnancy_category
    row.paediatric_caution = payload.paediatric_caution
    row.renal_caution = payload.renal_caution
    row.notes = payload.notes
    row.status = "ACTIVE"
    db.commit()
    return {"medication_id": str(payload.medication_id), "status": "ACTIVE"}
