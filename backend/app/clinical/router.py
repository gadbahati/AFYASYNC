from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit.service import record_audit
from app.auth.dependencies import get_facility_context, require_permission
from app.clinical.schemas import (
    ClinicalTimelineSummary,
    ConsultationCreate,
    ConsultationResponse,
    DiagnosisCreate,
    DiagnosisResponse,
    VitalCreate,
    VitalResponse,
)
from app.clinical.service import (
    add_diagnosis,
    create_or_update_consultation,
    get_encounter_clinical_summary,
    record_vitals,
)
from app.database import get_db
from app.encounters.models import Encounter
from app.rbac.models import Staff, User

router = APIRouter(prefix="/api/v1/encounters", tags=["Clinical"])


def _encounter(db: Session, encounter_id: UUID, facility_id: UUID) -> Encounter:
    encounter = db.get(Encounter, encounter_id)
    if encounter is None:
        raise HTTPException(status_code=404, detail="ENCOUNTER_NOT_FOUND")
    if encounter.facility_id != facility_id:
        raise HTTPException(status_code=403, detail="FACILITY_ACCESS_DENIED")
    return encounter


def _staff(db: Session, user: User, facility_id: UUID) -> Staff:
    staff = db.scalar(
        select(Staff).where(
            Staff.person_id == user.person_id,
            Staff.facility_id == facility_id,
            Staff.status == "ACTIVE",
        ).limit(1)
    )
    if staff is None:
        raise HTTPException(status_code=403, detail="FACILITY_ACCESS_DENIED")
    return staff


@router.get("/{encounter_id}/clinical", response_model=ClinicalTimelineSummary)
def get_clinical_timeline(
    encounter_id: UUID,
    user: User = Depends(require_permission("clinical.record.read")),
    facility_id: UUID = Depends(get_facility_context),
    db: Session = Depends(get_db),
) -> ClinicalTimelineSummary:
    try:
        summary = get_encounter_clinical_summary(db, encounter_id, facility_id)
    except ValueError as exc:
        code = str(exc)
        if code == "ENCOUNTER_NOT_FOUND":
            raise HTTPException(status_code=404, detail=code) from exc
        if code == "FACILITY_ACCESS_DENIED":
            raise HTTPException(status_code=403, detail=code) from exc
        raise HTTPException(status_code=400, detail=code) from exc

    encounter = summary["encounter"]
    record_audit(
        db,
        action="VIEW_CLINICAL_TIMELINE",
        resource_type="ENCOUNTER",
        resource_id=str(encounter.id),
        result="SUCCESS",
        user_id=user.id,
        facility_id=facility_id,
        patient_id=encounter.patient_id,
        metadata={
            "vitals_count": len(summary["vitals"]),
            "diagnoses_count": len(summary["diagnoses"]),
            "has_consultation": summary["consultation"] is not None,
        },
        commit=True,
    )
    return ClinicalTimelineSummary(
        encounter=encounter,
        vitals=summary["vitals"],
        consultation=summary["consultation"],
        diagnoses=summary["diagnoses"],
    )


@router.post("/{encounter_id}/vitals", response_model=VitalResponse, status_code=status.HTTP_201_CREATED)
def create_vitals(
    encounter_id: UUID,
    payload: VitalCreate,
    user: User = Depends(require_permission("clinical.vitals.write")),
    facility_id: UUID = Depends(get_facility_context),
    db: Session = Depends(get_db),
) -> VitalResponse:
    encounter = _encounter(db, encounter_id, facility_id)
    try:
        return record_vitals(
            db,
            encounter.id,
            _staff(db, user, facility_id).id,
            payload.model_dump(exclude_none=True),
            actor_user_id=user.id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/{encounter_id}/consultation", response_model=ConsultationResponse)
def save_consultation(
    encounter_id: UUID,
    payload: ConsultationCreate,
    user: User = Depends(require_permission("clinical.consultation.write")),
    facility_id: UUID = Depends(get_facility_context),
    db: Session = Depends(get_db),
) -> ConsultationResponse:
    encounter = _encounter(db, encounter_id, facility_id)
    try:
        return create_or_update_consultation(
            db,
            encounter.id,
            _staff(db, user, facility_id).id,
            payload.model_dump(),
            actor_user_id=user.id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exp


@router.post("/{encounter_id}/diagnoses", response_model=DiagnosisResponse, status_code=status.HTTP_201_CREATED)
def create_diagnosis(
    encounter_id: UUID,
    payload: DiagnosisCreate,
    user: User = Depends(require_permission("clinical.diagnosis.write")),
    facility_id: UUID = Depends(get_facility_context),
    db: Session = Depends(get_db),
) -> DiagnosisResponse:
    encounter = _encounter(db, encounter_id, facility_id)
    try:
        return add_diagnosis(
            db,
            encounter.id,
            _staff(db, user, facility_id).id,
            payload.model_dump(),
            actor_user_id=user.id,
        )
    except ValueError as exp:
        raise HTTPException(status_code=400, detail=str(exc)) from exp
