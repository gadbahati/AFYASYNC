from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.audit.service import record_audit
from app.auth.dependencies import get_facility_context, require_permission
from app.database import get_db
from app.encounters.schemas import EncounterListResponse
from app.encounters.service import list_patient_encounters_for_facility
from app.patients.schemas import PatientCreate, PatientFacilityResponse, PatientFacilityStatusUpdate, PatientListResponse, PatientResponse, PatientSearchResult, PatientUpdate
from app.patients.service import create_patient, enroll_patient_in_facility, get_patient_facility_enrollments, get_patient_for_facility, list_patients_for_facility, search_patients, update_patient, update_patient_facility_status
from app.rbac.models import User

router = APIRouter(prefix="/api/v1/patients", tags=["Patients"])


def _response(patient, afya_id: str | None = None) -> PatientResponse:
    resolved_afya_id = afya_id if afya_id is not None else patient.afya_identity.afya_id
    return PatientResponse(
        id=patient.id,
        afya_id=resolved_afya_id,
        first_name=patient.first_name,
        middle_name=patient.middle_name,
        last_name=patient.last_name,
        date_of_birth=patient.date_of_birth,
        sex=patient.sex,
        phone=patient.phone,
        email=patient.email,
        address=getattr(patient, "address", None),
        emergency_contact_name=getattr(patient, "emergency_contact_name", None),
        emergency_contact_phone=getattr(patient, "emergency_contact_phone", None),
        next_of_kin_name=getattr(patient, "next_of_kin_name", None),
        next_of_kin_phone=getattr(patient, "next_of_kin_phone", None),
        status=patient.status,
    )


@router.post("", response_model=PatientResponse, status_code=status.HTTP_201_CREATED)
def register_patient(payload: PatientCreate, user: User = Depends(require_permission("patients.create")), facility_id: UUID = Depends(get_facility_context), db: Session = Depends(get_db)) -> PatientResponse:
    try:
        patient = create_patient(db, payload, actor_user_id=user.id, facility_id=facility_id)
    except ValueError as exc:
        if str(exc) == "DUPLICATE_PATIENT":
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail={"code": "DUPLICATE_PATIENT", "message": "A possible existing patient was found."}) from exc
        raise
    return _response(patient)


@router.get("", response_model=PatientListResponse)
def list_patient_records(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    enrollment_status: Literal["ACTIVE", "INACTIVE"] | None = Query(default="ACTIVE"),
    user: User = Depends(require_permission("patients.record.read")),
    facility_id: UUID = Depends(get_facility_context),
    db: Session = Depends(get_db),
) -> PatientListResponse:
    """List patients enrolled at the authenticated facility only.

    Never returns patients that exist only at other facilities.
    """
    try:
        results, total = list_patients_for_facility(
            db,
            facility_id,
            limit=limit,
            offset=offset,
            enrollment_status=enrollment_status,
        )
    except ValueError as exc:
        if str(exc) == "INVALID_ENROLLMENT_STATUS":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": "INVALID_ENROLLMENT_STATUS", "message": "Enrollment status must be ACTIVE or INACTIVE."},
            ) from exc
        raise

    record_audit(
        db,
        action="LIST_PATIENT_RECORDS",
        resource_type="PERSON",
        resource_id=str(facility_id),
        result="SUCCESS",
        user_id=user.id,
        facility_id=facility_id,
        metadata={"count": len(results), "total": total, "limit": limit, "offset": offset, "enrollment_status": enrollment_status},
        commit=True,
    )
    return PatientListResponse(
        items=[_response(person, identity.afya_id) for person, identity in results],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/search", response_model=list[PatientSearchResult])
def search_patient_records(q: str = Query(min_length=2, max_length=100), limit: int = Query(default=20, ge=1, le=50), _: User = Depends(require_permission("patients.search")), facility_id: UUID = Depends(get_facility_context), db: Session = Depends(get_db)) -> list[PatientSearchResult]:
    results = search_patients(db, q, facility_id, limit)
    return [PatientSearchResult(id=person.id, afya_id=identity.afya_id, full_name=" ".join(filter(None, [person.first_name, person.middle_name, person.last_name])), phone=person.phone, status=person.status) for person, identity in results]


@router.get("/{patient_id}", response_model=PatientResponse)
def get_patient_record(patient_id: UUID, user: User = Depends(require_permission("patients.record.read")), facility_id: UUID = Depends(get_facility_context), db: Session = Depends(get_db)) -> PatientResponse:
    patient = get_patient_for_facility(db, patient_id, facility_id)
    if patient is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"code": "PATIENT_NOT_FOUND", "message": "Patient record not found."})
    record_audit(db, action="VIEW_PATIENT_RECORD", resource_type="PERSON", resource_id=str(patient.id), result="SUCCESS", user_id=user.id, facility_id=facility_id, patient_id=patient.id, commit=True)
    return _response(patient)


@router.get("/{patient_id}/encounters", response_model=EncounterListResponse)
def list_patient_encounter_timeline(
    patient_id: UUID,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    user: User = Depends(require_permission("clinical.record.read")),
    facility_id: UUID = Depends(get_facility_context),
    db: Session = Depends(get_db),
) -> EncounterListResponse:
    """Clinical timeline backbone: encounters for this patient at this facility only."""
    try:
        items, total = list_patient_encounters_for_facility(
            db, patient_id, facility_id, limit=limit, offset=offset
        )
    except ValueError as exc:
        code = str(exc)
        if code == "PATIENT_NOT_IN_FACILITY":
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"code": code, "message": "Patient not enrolled at this facility."}) from exc
        raise
    record_audit(
        db,
        action="VIEW_PATIENT_ENCOUNTER_TIMELINE",
        resource_type="PERSON",
        resource_id=str(patient_id),
        result="SUCCESS",
        user_id=user.id,
        facility_id=facility_id,
        patient_id=patient_id,
        metadata={"count": len(items), "total": total},
        commit=True,
    )
    return EncounterListResponse(items=items, total=total, limit=limit, offset=offset)


@router.get("/{patient_id}/enrollments", response_model=list[PatientFacilityResponse])
def list_patient_enrollments(patient_id: UUID, user: User = Depends(require_permission("patients.record.read")), facility_id: UUID = Depends(get_facility_context), db: Session = Depends(get_db)) -> list[PatientFacilityResponse]:
    patient = get_patient_for_facility(db, patient_id, facility_id)
    if patient is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"code": "PATIENT_NOT_FOUND", "message": "Patient record not found."})
    enrollments = get_patient_facility_enrollments(db, patient_id, facility_id)
    record_audit(db, action="VIEW_PATIENT_ENROLLMENTS", resource_type="PERSON", resource_id=str(patient_id), result="SUCCESS", user_id=user.id, facility_id=facility_id, patient_id=patient_id, metadata={"enrollment_count": len(enrollments)}, commit=True)
    return enrollments


@router.post("/{patient_id}/enrollment", response_model=PatientFacilityResponse, status_code=status.HTTP_201_CREATED)
def enroll_patient_record(patient_id: UUID, user: User = Depends(require_permission("patients.record.write")), facility_id: UUID = Depends(get_facility_context), db: Session = Depends(get_db)) -> PatientFacilityResponse:
    try:
        membership = enroll_patient_in_facility(db, patient_id, facility_id, actor_user_id=user.id)
    except ValueError as exc:
        code = str(exc)
        if code == "PATIENT_NOT_FOUND":
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"code": code, "message": "Patient record not found."}) from exc
        if code == "PATIENT_ALREADY_ENROLLED":
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail={"code": code, "message": "Patient is already enrolled at this facility."}) from exc
        raise
    return membership


@router.patch("/{patient_id}/enrollment", response_model=PatientFacilityResponse)
def update_patient_enrollment(patient_id: UUID, payload: PatientFacilityStatusUpdate, user: User = Depends(require_permission("patients.record.write")), facility_id: UUID = Depends(get_facility_context), db: Session = Depends(get_db)) -> PatientFacilityResponse:
    try:
        membership = update_patient_facility_status(db, patient_id, facility_id, payload.status, actor_user_id=user.id)
    except ValueError as exc:
        code = str(exc)
        if code == "PATIENT_NOT_IN_FACILITY":
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"code": code, "message": "Patient enrollment not found."}) from exc
        if code == "INVALID_PATIENT_FACILITY_STATUS":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={"code": code, "message": "Enrollment status must be ACTIVE or INACTIVE."}) from exc
        if code == "PATIENT_FACILITY_STATUS_UNCHANGED":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={"code": code, "message": "Enrollment status is already set to the requested value."}) from exc
        raise
    return membership


@router.patch("/{patient_id}", response_model=PatientResponse)
def update_patient_record(patient_id: UUID, payload: PatientUpdate, user: User = Depends(require_permission("patients.record.write")), facility_id: UUID = Depends(get_facility_context), db: Session = Depends(get_db)) -> PatientResponse:
    patient = get_patient_for_facility(db, patient_id, facility_id)
    if patient is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"code": "PATIENT_NOT_FOUND", "message": "Patient record not found."})
    try:
        patient = update_patient(db, patient, payload, actor_user_id=user.id, facility_id=facility_id)
    except ValueError as exc:
        code = str(exc)
        if code == "DUPLICATE_PHONE":
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail={"code": code, "message": "Phone number is already associated with another patient."}) from exc
        if code == "NO_CHANGES":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={"code": code, "message": "At least one patient field must be supplied."}) from exc
        if code == "PATIENT_NOT_IN_FACILITY":
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"code": code, "message": "Patient record not found."}) from exc
        if code == "INVALID_PATIENT_STATUS":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={"code": code, "message": "Patient status must be ACTIVE or INACTIVE."}) from exc
        raise
    return _response(patient)
