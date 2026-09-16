from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit.service import record_audit
from app.auth.dependencies import get_facility_context, require_permission
from app.clinical.models import CarePlan
from app.clinical.schemas import CarePlanCreate, CarePlanResponse, CarePlanUpdate, ClinicalTimelineSummary, ConsultationCreate, ConsultationResponse, DiagnosisCreate, DiagnosisResponse, VitalCreate, VitalResponse
from app.clinical.service import add_diagnosis, create_care_plan, create_or_update_consultation, get_encounter_clinical_summary, list_care_plans, record_vitals, update_care_plan
from app.database import get_db
from app.encounters.models import Encounter
from app.rbac.models import Staff, User

router = APIRouter(prefix="/api/v1/encounters", tags=["Clinical"])


def _encounter(db: Session, encounter_id: UUID, facility_id: UUID) -> Encounter:
    encounter = db.get(Encounter, encounter_id)
    if encounter is None: raise HTTPException(status_code=404, detail="ENCOUNTER_NOT_FOUND")
    if encounter.facility_id != facility_id: raise HTTPException(status_code=403, detail="FACILITY_ACCESS_DENIED")
    return encounter


def _staff(db: Session, user: User, facility_id: UUID) -> Staff:
    staff = db.scalar(select(Staff).where(Staff.person_id == user.person_id, Staff.facility_id == facility_id, Staff.status == "ACTIVE").limit(1))
    if staff is None: raise HTTPException(status_code=403, detail="FACILITY_ACCESS_DENIED")
    return staff


@router.get("/{encounter_id}/clinical", response_model=ClinicalTimelineSummary)
def get_clinical_timeline(encounter_id: UUID, user: User = Depends(require_permission("clinical.record.read")), facility_id: UUID = Depends(get_facility_context), db: Session = Depends(get_db)) -> ClinicalTimelineSummary:
    try:
        summary = get_encounter_clinical_summary(db, encounter_id, facility_id)
        response = ClinicalTimelineSummary(encounter=summary["encounter"], vitals=summary["vitals"], consultation=summary["consultation"], diagnoses=summary["diagnoses"], lab_orders=summary["lab_orders"], prescriptions=summary["prescriptions"])
        encounter = summary["encounter"]
        record_audit(db, action="VIEW_CLINICAL_TIMELINE", resource_type="ENCOUNTER", resource_id=str(encounter.id), result="SUCCESS", user_id=user.id, facility_id=facility_id, patient_id=encounter.patient_id, metadata={"vitals_count": len(summary["vitals"]), "diagnoses_count": len(summary["diagnoses"]), "has_consultation": summary["consultation"] is not None, "lab_orders_count": len(summary["lab_orders"]), "prescriptions_count": len(summary["prescriptions"])}, commit=True)
        return response
    except ValueError as err:
        code = str(err)
        if code == "ENCOUNTER_NOT_FOUND": raise HTTPException(status_code=404, detail=code) from err
        if code == "FACILITY_ACCESS_DENIED": raise HTTPException(status_code=403, detail=code) from err
        raise HTTPException(status_code=400, detail=code) from err


@router.post("/{encounter_id}/vitals", response_model=VitalResponse, status_code=status.HTTP_201_CREATED)
def create_vitals(encounter_id: UUID, payload: VitalCreate, user: User = Depends(require_permission("clinical.vitals.write")), facility_id: UUID = Depends(get_facility_context), db: Session = Depends(get_db)) -> VitalResponse:
    encounter = _encounter(db, encounter_id, facility_id)
    try: return record_vitals(db, encounter.id, _staff(db, user, facility_id).id, payload.model_dump(exclude_none=True), actor_user_id=user.id)
    except ValueError as err: raise HTTPException(status_code=400, detail=str(err)) from err


@router.post("/{encounter_id}/consultation", response_model=ConsultationResponse)
def save_consultation(encounter_id: UUID, payload: ConsultationCreate, user: User = Depends(require_permission("clinical.consultation.write")), facility_id: UUID = Depends(get_facility_context), db: Session = Depends(get_db)) -> ConsultationResponse:
    encounter = _encounter(db, encounter_id, facility_id)
    try: return create_or_update_consultation(db, encounter.id, _staff(db, user, facility_id).id, payload.model_dump(), actor_user_id=user.id)
    except ValueError as err: raise HTTPException(status_code=400, detail=str(err)) from err


@router.post("/{encounter_id}/diagnoses", response_model=DiagnosisResponse, status_code=status.HTTP_201_CREATED)
def create_diagnosis(encounter_id: UUID, payload: DiagnosisCreate, user: User = Depends(require_permission("clinical.diagnosis.write")), facility_id: UUID = Depends(get_facility_context), db: Session = Depends(get_db)) -> DiagnosisResponse:
    encounter = _encounter(db, encounter_id, facility_id)
    try: return add_diagnosis(db, encounter.id, _staff(db, user, facility_id).id, payload.model_dump(), actor_user_id=user.id)
    except ValueError as err: raise HTTPException(status_code=400, detail=str(err)) from err


@router.get("/patients/{patient_id}/care-plans", response_model=list[CarePlanResponse])
def get_patient_care_plans(patient_id: UUID, status_filter: str | None = Query(default=None, alias="status", pattern="^(ACTIVE|COMPLETED|CANCELLED)$"), user: User = Depends(require_permission("clinical.care_plan.read")), facility_id: UUID = Depends(get_facility_context), db: Session = Depends(get_db)):
    try:
        plans = list_care_plans(db, patient_id, facility_id, status_filter)
        record_audit(db, action="LIST_CARE_PLANS", resource_type="PERSON", resource_id=str(patient_id), result="SUCCESS", user_id=user.id, facility_id=facility_id, patient_id=patient_id, metadata={"count": len(plans)}, commit=True)
        return plans
    except ValueError as exc:
        code = str(exc)
        raise HTTPException(status_code=404 if code in {"PATIENT_NOT_FOUND", "PATIENT_NOT_IN_FACILITY"} else 400, detail=code) from exc


@router.post("/patients/{patient_id}/care-plans", response_model=CarePlanResponse, status_code=status.HTTP_201_CREATED)
def create_patient_care_plan(patient_id: UUID, payload: CarePlanCreate, user: User = Depends(require_permission("clinical.care_plan.write")), facility_id: UUID = Depends(get_facility_context), db: Session = Depends(get_db)):
    try:
        return create_care_plan(db, patient_id, facility_id, user.id, payload.model_dump(exclude_none=True))
    except ValueError as exc:
        code = str(exc)
        raise HTTPException(status_code=404 if code in {"PATIENT_NOT_FOUND", "PATIENT_NOT_IN_FACILITY", "ENCOUNTER_NOT_FOUND"} else 403 if code == "FACILITY_ACCESS_DENIED" else 400, detail=code) from exc


@router.patch("/patients/{patient_id}/care-plans/{care_plan_id}", response_model=CarePlanResponse)
def update_patient_care_plan(patient_id: UUID, care_plan_id: UUID, payload: CarePlanUpdate, user: User = Depends(require_permission("clinical.care_plan.write")), facility_id: UUID = Depends(get_facility_context), db: Session = Depends(get_db)):
    plan = db.get(CarePlan, care_plan_id)
    if plan is None or plan.patient_id != patient_id:
        raise HTTPException(status_code=404, detail="CARE_PLAN_NOT_FOUND")
    try:
        return update_care_plan(db, plan, user.id, facility_id, payload.model_dump(exclude_unset=True))
    except ValueError as exc:
        code = str(exc)
        raise HTTPException(status_code=409 if code == "INVALID_CARE_PLAN_TRANSITION" else 403 if code == "FACILITY_ACCESS_DENIED" else 404 if code == "ENCOUNTER_NOT_FOUND" else 400, detail=code) from exc
