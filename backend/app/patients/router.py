from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.auth.dependencies import require_permission
from app.database import get_db
from app.patients.schemas import PatientCreate, PatientResponse, PatientSearchResult
from app.patients.service import create_patient, search_patients
from app.rbac.models import User

router = APIRouter(prefix="/api/v1/patients", tags=["Patients"])


@router.post("", response_model=PatientResponse, status_code=status.HTTP_201_CREATED)
def register_patient(payload: PatientCreate, db: Session = Depends(get_db)) -> PatientResponse:
    try:
        patient = create_patient(db, payload)
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
    db: Session = Depends(get_db),
) -> list[PatientSearchResult]:
    results = search_patients(db, q, limit)
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
