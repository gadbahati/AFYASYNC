from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.audit.service import record_audit
from app.auth.dependencies import get_facility_context, require_permission
from app.database import get_db
from app.patients.schemas import PatientCreate, PatientResponse, PatientSearchResult
from app.patients.service import create_patient, get_patient_for_facility, search_patients
from app.rbac.models import User

router = APIRouter(prefix="/api/v1/patients", tags=["Patients"])


@router.post("", response_model=PatientResponse, status_code=status.HTTP_201_CREATED)
def register_patient(
    payload: PatientCreate,
    user: User = Depends(require_permission("patients.create")),
    facility_id: UUID = Depends(get_facility_context),
    db: Session = Depends(get_db),
) -> PatientResponse:
    try:
        patient = create_patient(db, payload, actor_user_id=user.id, facility_id=facility_id)
    except ValueError as exc:
        if str(exc) == "DUPLICATE_PATIENT":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"code": "DUPLICATE_PATIENT", "message": "A possible existing patient was found."},
            ) from exc
        raise

    return PatientResponse(
        id=patient.id,
        afya_id=patient.afya_identity.afya_id,
        first_name=patient.first_name,
        middle_name=patient.middle_name,
        last_name=patient.last_name,
        date_of_birth=patient.date_of_birth,
        sex=patient.sex,
        phone=patient.phone,
        email=patient.email,
        status=patient.status,
    )


@router.get("/search", response_model=list[PatientSearchResult])
def search_patient_records(
    q: str = Query(min_length=2, max_length=100),
    limit: int = Query(default=20, ge=1, le=50),
    _: User = Depends(require_permission("patients.search")),
    facility_id: UUID = Depends(get_facility_context),
    db: Session = Depends(get_db),
) -> list[PatientSearchResult]:
    results = search_patients(db, q, facility_id, limit)
    return [
        PatientSearchResult(
            id=person.id,
            afya_id=identity.afya_id,
            full_name=" ".join(filter(None, [person.first_name, person.middle_name, person.last_name])),
            phone=person.phone,
            status=person.status,
        )
        for person, identity in results
    ]


@router.get("/{patient_id}", response_model=PatientResponse)
def get_patient_record(
    patient_id: UUID,
    user: User = Depends(require_permission("patients.record.read")),
    facility_id: UUID = Depends(get_facility_context),
    db: Session = Depends(get_db),
) -> PatientResponse:
    patient = get_patient_for_facility(db, patient_id, facility_id)
    if patient is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "PATIENT_NOT_FOUND", "message": "Patient record not found."},
        )

    record_audit(
        db,
        action="VIEW_PATIENT_RECORD",
        resource_type="PERSON",
        resource_id=str(patient.id),
        result="SUCCESS",
        user_id=user.id,
        facility_id=facility_id,
        patient_id=patient.id,
        commit=True,
    )

    return PatientResponse(
        id=patient.id,
        afya_id=patient.afya_identity.afya_id,
        first_name=patient.first_name,
        middle_name=patient.middle_name,
        last_name=patient.last_name,
        date_of_birth=patient.date_of_birth,
        sex=patient.sex,
        phone=patient.phone,
        email=patient.email,
        status=patient.status,
    )
