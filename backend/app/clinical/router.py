from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit.service import record_audit
from app.auth.dependencies import get_facility_context, require_permission
from app.clinical.discharge_models import ClinicalDischarge
from app.clinical.discharge_service import DischargeError, discharge_encounter, get_discharge
from app.clinical.orders_routes import orders_router
from app.clinical.models import Allergy, CarePlan, Procedure, ClinicalNote
from app.clinical.triage import latest_triage, record_triage
from app.clinical.schemas import (
    AllergyCreate,
    AllergyResponse,
    AllergyUpdate,
    CarePlanCreate,
    CarePlanResponse,
    CarePlanUpdate,
    ClinicalTimelineSummary,
    ConsultationCreate,
    ConsultationResponse,
    DiagnosisCreate,
    DiagnosisResponse,
    ProcedureCreate,
    ProcedureResponse,
    ClinicalNoteCreate,
    ClinicalNoteResponse,
    TriageCreate,
    TriageResponse,
    VitalCreate,
    VitalResponse,
)
from app.clinical.service import (
    add_diagnosis,
    add_procedure,
    create_allergy,
    create_care_plan,
    create_or_update_consultation,
    get_encounter_clinical_summary,
    list_allergies,
    list_care_plans,
    list_clinical_notes,
    list_procedures,
    record_vitals,
    save_clinical_note,
    update_allergy,
    update_care_plan,
)
from app.database import get_db
from app.encounters.models import Encounter
from app.pharmacy.models import Medication
from app.rbac.models import Staff, User

router = APIRouter()
encounter_router = APIRouter(prefix="/api/v1/encounters", tags=["Clinical"])
care_plan_router = APIRouter(prefix="/api/v1/patients", tags=["Care Plans"])
allergy_router = APIRouter(prefix="/api/v1/patients", tags=["Clinical Safety"])


def _encounter(db: Session, encounter_id: UUID, facility_id: UUID) -> Encounter:
    enc = db.get(Encounter, encounter_id)
    if enc is None:
        raise HTTPException(status_code=404, detail="ENCOUNTER_NOT_FOUND")
    if enc.facility_id != facility_id:
        raise HTTPException(status_code=403, detail="FACILITY_ACCESS_DENIED")
    return enc


@encounter_router.get("/{encounter_id}/clinical-timeline", response_model=ClinicalTimelineSummary)
def get_clinical_timeline(
    encounter_id: UUID,
    user: User = Depends(require_permission("clinical.record.read")),
    facility_id: UUID = Depends(get_facility_context),
    db: Session = Depends(get_db),
):
    _ = user
    _encounter(db, encounter_id, facility_id)
    return get_encounter_clinical_summary(db, encounter_id)


@encounter_router.post("/{encounter_id}/vitals", response_model=VitalResponse, status_code=201)
def create_vitals(
    encounter_id: UUID,
    payload: VitalCreate,
    user: User = Depends(require_permission("clinical.vitals.write")),
    facility_id: UUID = Depends(get_facility_context),
    db: Session = Depends(get_db),
):
    _encounter(db, encounter_id, facility_id)
    return record_vitals(db, encounter_id, payload, actor_user_id=user.id)


@encounter_router.get("/{encounter_id}/triage", response_model=TriageResponse | None)
def get_latest_triage(
    encounter_id: UUID,
    user: User = Depends(require_permission("clinical.record.read")),
    facility_id: UUID = Depends(get_facility_context),
    db: Session = Depends(get_db),
):
    _ = user
    _encounter(db, encounter_id, facility_id)
    return latest_triage(db, encounter_id)


@encounter_router.post("/{encounter_id}/triage", response_model=TriageResponse, status_code=201)
def create_triage(
    encounter_id: UUID,
    payload: TriageCreate,
    user: User = Depends(require_permission("clinical.vitals.write")),
    facility_id: UUID = Depends(get_facility_context),
    db: Session = Depends(get_db),
):
    _encounter(db, encounter_id, facility_id)
    return record_triage(db, encounter_id, payload, actor_user_id=user.id)


@encounter_router.post("/{encounter_id}/consultation", response_model=ConsultationResponse)
def save_consultation(
    encounter_id: UUID,
    payload: ConsultationCreate,
    user: User = Depends(require_permission("clinical.consultation.write")),
    facility_id: UUID = Depends(get_facility_context),
    db: Session = Depends(get_db),
):
    _encounter(db, encounter_id, facility_id)
    return create_or_update_consultation(db, encounter_id, payload, actor_user_id=user.id)


@encounter_router.get("/{encounter_id}/procedures", response_model=list[ProcedureResponse])
def get_procedures(
    encounter_id: UUID,
    user: User = Depends(require_permission("clinical.record.read")),
    facility_id: UUID = Depends(get_facility_context),
    db: Session = Depends(get_db),
):
    _ = user
    _encounter(db, encounter_id, facility_id)
    return list_procedures(db, encounter_id)


@encounter_router.post("/{encounter_id}/procedures", response_model=ProcedureResponse, status_code=201)
def create_procedure(
    encounter_id: UUID,
    payload: ProcedureCreate,
    user: User = Depends(require_permission("clinical.procedure.write")),
    facility_id: UUID = Depends(get_facility_context),
    db: Session = Depends(get_db),
):
    _encounter(db, encounter_id, facility_id)
    return add_procedure(db, encounter_id, payload, actor_user_id=user.id)


@encounter_router.get("/{encounter_id}/notes", response_model=list[ClinicalNoteResponse])
def get_clinical_notes(
    encounter_id: UUID,
    user: User = Depends(require_permission("clinical.record.read")),
    facility_id: UUID = Depends(get_facility_context),
    db: Session = Depends(get_db),
):
    _ = user
    _encounter(db, encounter_id, facility_id)
    return list_clinical_notes(db, encounter_id)


@encounter_router.post("/{encounter_id}/notes", response_model=ClinicalNoteResponse, status_code=201)
def create_clinical_note(
    encounter_id: UUID,
    payload: ClinicalNoteCreate,
    user: User = Depends(require_permission("clinical.note.write")),
    facility_id: UUID = Depends(get_facility_context),
    db: Session = Depends(get_db),
):
    _encounter(db, encounter_id, facility_id)
    return save_clinical_note(db, encounter_id, payload, actor_user_id=user.id)


@encounter_router.post("/{encounter_id}/diagnoses", response_model=DiagnosisResponse, status_code=201)
def create_diagnosis(
    encounter_id: UUID,
    payload: DiagnosisCreate,
    user: User = Depends(require_permission("clinical.diagnosis.write")),
    facility_id: UUID = Depends(get_facility_context),
    db: Session = Depends(get_db),
):
    _encounter(db, encounter_id, facility_id)
    return add_diagnosis(db, encounter_id, payload, actor_user_id=user.id)


@encounter_router.post("/{encounter_id}/discharge", status_code=201)
def post_discharge(
    encounter_id: UUID,
    payload: dict,
    db: Session = Depends(get_db),
    facility_id: UUID = Depends(get_facility_context),
    user: User = Depends(require_permission("clinical.note.write")),
):
    """Phase 131 — discharge / close encounter with disposition."""
    from datetime import date as date_cls

    follow = payload.get("follow_up_date")
    follow_date = None
    if follow:
        follow_date = date_cls.fromisoformat(str(follow)) if isinstance(follow, str) else follow
    try:
        row = discharge_encounter(
            db,
            encounter_id=encounter_id,
            facility_id=facility_id,
            actor_user_id=user.id,
            disposition=str(payload.get("disposition") or ""),
            outcome=str(payload.get("outcome") or "STABLE"),
            follow_up_instructions=payload.get("follow_up_instructions"),
            follow_up_date=follow_date,
            discharge_summary=payload.get("discharge_summary"),
        )
    except DischargeError as exc:
        code = str(exc)
        status_code = 404 if code == "ENCOUNTER_NOT_FOUND" else (403 if code == "FACILITY_ACCESS_DENIED" else 409)
        raise HTTPException(status_code=status_code, detail=code) from exc
    return {
        "id": str(row.id),
        "encounter_id": str(row.encounter_id),
        "disposition": row.disposition,
        "outcome": row.outcome,
        "follow_up_instructions": row.follow_up_instructions,
        "follow_up_date": row.follow_up_date.isoformat() if row.follow_up_date else None,
        "discharge_summary": row.discharge_summary,
        "discharged_at": row.discharged_at.isoformat() if row.discharged_at else None,
        "developer": "BAHATI GAD WANGWE",
    }


@encounter_router.get("/{encounter_id}/discharge")
def read_discharge(
    encounter_id: UUID,
    db: Session = Depends(get_db),
    facility_id: UUID = Depends(get_facility_context),
    user: User = Depends(require_permission("clinical.record.read")),
):
    _ = user
    try:
        row = get_discharge(db, encounter_id=encounter_id, facility_id=facility_id)
    except DischargeError as exc:
        code = str(exc)
        status_code = 404 if code == "ENCOUNTER_NOT_FOUND" else 403
        raise HTTPException(status_code=status_code, detail=code) from exc
    if row is None:
        raise HTTPException(status_code=404, detail="DISCHARGE_NOT_FOUND")
    return {
        "id": str(row.id),
        "encounter_id": str(row.encounter_id),
        "disposition": row.disposition,
        "outcome": row.outcome,
        "follow_up_instructions": row.follow_up_instructions,
        "follow_up_date": row.follow_up_date.isoformat() if row.follow_up_date else None,
        "discharge_summary": row.discharge_summary,
        "discharged_at": row.discharged_at.isoformat() if row.discharged_at else None,
    }


@care_plan_router.get("/{patient_id}/care-plans", response_model=list[CarePlanResponse])
def get_patient_care_plans(
    patient_id: UUID,
    status_filter: str | None = Query(default=None, alias="status"),
    user: User = Depends(require_permission("clinical.record.read")),
    facility_id: UUID = Depends(get_facility_context),
    db: Session = Depends(get_db),
):
    _ = user, facility_id
    return list_care_plans(db, patient_id, status_filter=status_filter)


@care_plan_router.post("/{patient_id}/care-plans", response_model=CarePlanResponse, status_code=201)
def create_patient_care_plan(
    patient_id: UUID,
    payload: CarePlanCreate,
    user: User = Depends(require_permission("clinical.care_plan.write")),
    facility_id: UUID = Depends(get_facility_context),
    db: Session = Depends(get_db),
):
    _ = facility_id
    return create_care_plan(db, patient_id, payload, actor_user_id=user.id)


@care_plan_router.patch("/{patient_id}/care-plans/{care_plan_id}", response_model=CarePlanResponse)
def update_patient_care_plan(
    patient_id: UUID,
    care_plan_id: UUID,
    payload: CarePlanUpdate,
    user: User = Depends(require_permission("clinical.care_plan.write")),
    facility_id: UUID = Depends(get_facility_context),
    db: Session = Depends(get_db),
):
    _ = facility_id
    return update_care_plan(db, patient_id, care_plan_id, payload, actor_user_id=user.id)


@allergy_router.get("/{patient_id}/allergies", response_model=list[AllergyResponse])
def get_patient_allergies(
    patient_id: UUID,
    include_inactive: bool = Query(default=False),
    user: User = Depends(require_permission("clinical.record.read")),
    facility_id: UUID = Depends(get_facility_context),
    db: Session = Depends(get_db),
):
    _ = user, facility_id
    return list_allergies(db, patient_id, include_inactive=include_inactive)


@allergy_router.post("/{patient_id}/allergies", response_model=AllergyResponse, status_code=201)
def create_patient_allergy(
    patient_id: UUID,
    payload: AllergyCreate,
    user: User = Depends(require_permission("clinical.allergy.write")),
    facility_id: UUID = Depends(get_facility_context),
    db: Session = Depends(get_db),
):
    _ = facility_id
    return create_allergy(db, patient_id, payload, actor_user_id=user.id)


@allergy_router.patch("/{patient_id}/allergies/{allergy_id}", response_model=AllergyResponse)
def update_patient_allergy(
    patient_id: UUID,
    allergy_id: UUID,
    payload: AllergyUpdate,
    user: User = Depends(require_permission("clinical.allergy.write")),
    facility_id: UUID = Depends(get_facility_context),
    db: Session = Depends(get_db),
):
    _ = facility_id
    return update_allergy(db, patient_id, allergy_id, payload, actor_user_id=user.id)


@allergy_router.get("/{patient_id}/medication-safety/{medication_id}")
def check_medication_allergy_safety(
    patient_id: UUID,
    medication_id: UUID,
    user: User = Depends(require_permission("clinical.record.read")),
    facility_id: UUID = Depends(get_facility_context),
    db: Session = Depends(get_db),
):
    _ = facility_id
    medication = db.get(Medication, medication_id)
    if medication is None:
        raise HTTPException(status_code=404, detail="MEDICATION_NOT_FOUND")
    allergies = list_allergies(db, patient_id, include_inactive=False)
    conflicts = []
    name = (medication.name or "").lower()
    for a in allergies:
        substance = (getattr(a, "substance", None) or getattr(a, "allergen", "") or "").lower()
        if substance and substance in name:
            severity = getattr(a, "severity", "MODERATE") or "MODERATE"
            conflicts.append({"allergy_id": str(a.id), "substance": substance, "severity": severity})
    record_audit(
        db,
        action="MEDICATION_ALLERGY_CHECK",
        resource_type="MEDICATION",
        resource_id=str(medication.id),
        result="SUCCESS",
        user_id=user.id,
        facility_id=facility_id,
        patient_id=patient_id,
        metadata={"conflict_count": len(conflicts), "medication_id": str(medication.id)},
        commit=True,
    )
    return {
        "patient_id": str(patient_id),
        "medication_id": str(medication.id),
        "medication": medication.name,
        "safe_match": len(conflicts) == 0,
        "requires_clinical_review": any(item["severity"] in {"SEVERE", "LIFE_THREATENING"} for item in conflicts),
        "conflicts": conflicts,
    }


encounter_router.include_router(orders_router)
router.include_router(encounter_router)
router.include_router(care_plan_router)
router.include_router(allergy_router)
