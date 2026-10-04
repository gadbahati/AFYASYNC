from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.audit.service import record_audit
from app.auth.dependencies import get_facility_context, require_national_permission, require_permission
from app.context.service import resolve_facility_ids
from app.database import get_db
from app.encounters.schemas import EncounterListResponse
from app.encounters.service import list_patient_encounters_for_facility
from app.patients.record_schemas import PatientRecordSummaryResponse
from app.patients.mpi import find_mpi_candidates
from app.patients.mpi_schemas import MPIResponse
from app.patients.record_service import get_patient_record_summary
from app.patients.cross_facility import get_cross_facility_record
from app.patients.cross_facility_schemas import CrossFacilityRecordResponse, CrossFacilityMPIResponse
from app.patients.schemas import PatientCreate, PatientFacilityResponse, PatientFacilityStatusUpdate, PatientListResponse, PatientResponse, PatientSearchResult, PatientUpdate
from app.patients.service import create_patient, enroll_patient_in_facility, get_patient_facility_enrollments, get_patient_for_facility, list_patients_for_facility, search_patients, update_patient, update_patient_facility_status
from app.rbac.models import User

router = APIRouter(prefix="/api/v1/patients", tags=["Patients"])


def _response(patient, afya_id: str | None = None) -> PatientResponse:
    resolved_afya_id = afya_id if afya_id is not None else patient.afya_identity.afya_id
    return PatientResponse(
        id=patient.id, afya_id=resolved_afya_id, first_name=patient.first_name, middle_name=patient.middle_name,
        last_name=patient.last_name, date_of_birth=patient.date_of_birth, sex=patient.sex, phone=patient.phone,
        email=patient.email, address=getattr(patient, "address", None), emergency_contact_name=getattr(patient, "emergency_contact_name", None),
        emergency_contact_phone=getattr(patient, "emergency_contact_phone", None), next_of_kin_name=getattr(patient, "next_of_kin_name", None),
        next_of_kin_phone=getattr(patient, "next_of_kin_phone", None), status=patient.status,
    )


def _degraded_patient_record(db: Session, patient_id: UUID, facility_id: UUID) -> dict | None:
    db.rollback()
    patient = get_patient_for_facility(db, patient_id, facility_id)
    if patient is None:
        return None
    identity = getattr(patient, "afya_identity", None)
    if identity is None:
        return None
    enrollments = get_patient_facility_enrollments(db, patient_id, facility_id)
    enrollment_status = enrollments[0].status if enrollments else None
    encounters, _ = list_patient_encounters_for_facility(db, patient_id, facility_id, limit=100, offset=0)
    encounter_payload = [item.model_dump(mode="json") for item in encounters]
    return {
        "patient": {
            "id": str(patient.id), "afya_id": identity.afya_id, "first_name": patient.first_name,
            "middle_name": patient.middle_name, "last_name": patient.last_name, "date_of_birth": patient.date_of_birth,
            "sex": patient.sex, "phone": patient.phone, "email": patient.email, "address": getattr(patient, "address", None),
            "emergency_contact_name": getattr(patient, "emergency_contact_name", None),
            "emergency_contact_phone": getattr(patient, "emergency_contact_phone", None),
            "next_of_kin_name": getattr(patient, "next_of_kin_name", None),
            "next_of_kin_phone": getattr(patient, "next_of_kin_phone", None), "status": patient.status,
            "enrollment_status": enrollment_status, "registered_at": patient.created_at,
        },
        "allergies": [], "coverage": [], "encounters": encounter_payload, "laboratory": [], "prescriptions": [],
        "medication_actions": [], "admissions": [], "preauthorizations": [],
        "billing": {"charges": [], "invoices": [], "payments": []}, "claims": [], "appointments": [],
        "queue_history": [], "referrals": [], "transfers": [],
    }


@router.get("/mpi/cross-facility/candidates", response_model=CrossFacilityMPIResponse)
def cross_facility_mpi_candidates(
    first_name: str | None = Query(default=None, max_length=100),
    last_name: str | None = Query(default=None, max_length=100),
    date_of_birth: str | None = Query(default=None),
    phone: str | None = Query(default=None, max_length=30),
    national_id_number: str | None = Query(default=None, min_length=7, max_length=9),
    limit: int = Query(default=20, ge=1, le=50),
    user: User = Depends(require_national_permission("interoperability.patient.read")),
    facility_id: UUID = Depends(get_facility_context),
    db: Session = Depends(get_db),
) -> CrossFacilityMPIResponse:
    from datetime import date
    from app.context.service import resolve_facility_ids
    parsed_dob = None
    if date_of_birth:
        try:
            parsed_dob = date.fromisoformat(date_of_birth)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail={"code": "INVALID_DATE_OF_BIRTH", "message": "Use YYYY-MM-DD."}) from exc
    facility_ids = resolve_facility_ids(db, user=user, token_facility_id=facility_id, scope="network")
    try:
        candidates = find_mpi_candidates(
            db, facility_id=facility_id, facility_ids=facility_ids,
            first_name=first_name, last_name=last_name, date_of_birth=parsed_dob,
            phone=phone, national_id_number=national_id_number, limit=limit,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail={"code": str(exc), "message": "Provide at least one identity or demographic identifier."}) from exc
    record_audit(db, action="CROSS_FACILITY_MPI_SEARCH", resource_type="PERSON",
                 resource_id=str(facility_id), result="SUCCESS", user_id=user.id,
                 facility_id=facility_id,
                 metadata={"candidate_count": len(candidates), "facility_count": len(facility_ids)},
                 commit=True)
    return CrossFacilityMPIResponse(candidates=candidates, requires_review_before_access=bool(candidates))


@router.get("/cross-facility/{patient_id}/record", response_model=CrossFacilityRecordResponse)
def cross_facility_patient_record(
    patient_id: UUID,
    access_reason: str = Query(min_length=3, max_length=200),
    user: User = Depends(require_national_permission("interoperability.patient.read")),
    facility_id: UUID = Depends(get_facility_context),
    db: Session = Depends(get_db),
) -> CrossFacilityRecordResponse:
    from app.context.service import resolve_facility_ids
    facility_ids = resolve_facility_ids(db, user=user, token_facility_id=facility_id, scope="network")
    try:
        result = get_cross_facility_record(
            db, patient_id=patient_id, facility_ids=facility_ids,
            requesting_facility_id=facility_id, actor_user_id=user.id,
            access_reason=access_reason,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if result is None:
        raise HTTPException(status_code=404, detail={"code": "PATIENT_NOT_IN_AUTHORIZED_NETWORK", "message": "No active patient record was found within your authorized facility network."})
    return CrossFacilityRecordResponse(**result)


@router.get("/mpi/candidates", response_model=MPIResponse)
def mpi_candidates(
    first_name: str | None = Query(default=None, max_length=100),
    last_name: str | None = Query(default=None, max_length=100),
    date_of_birth: str | None = Query(default=None),
    phone: str | None = Query(default=None, max_length=30),
    national_id_number: str | None = Query(default=None, min_length=7, max_length=9),
    limit: int = Query(default=20, ge=1, le=50),
    user: User = Depends(require_permission("patients.create")),
    facility_id: UUID = Depends(get_facility_context),
    db: Session = Depends(get_db),
) -> MPIResponse:
    from datetime import date
    parsed_dob = None
    if date_of_birth:
        try:
            parsed_dob = date.fromisoformat(date_of_birth)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail={"code": "INVALID_DATE_OF_BIRTH", "message": "Use YYYY-MM-DD."}) from exc
    try:
        candidates = find_mpi_candidates(
            db,
            facility_id=facility_id,
            first_name=first_name,
            last_name=last_name,
            date_of_birth=parsed_dob,
            phone=phone,
            national_id_number=national_id_number,
            limit=limit,
        )
    except ValueError as exc:
        code = str(exc)
        raise HTTPException(status_code=422, detail={"code": code, "message": "Provide at least one identity or demographic identifier."}) from exc
    return MPIResponse(candidates=candidates, requires_review_before_registration=bool(candidates))


@router.post("", response_model=PatientResponse, status_code=status.HTTP_201_CREATED)
def register_patient(payload: PatientCreate, user: User = Depends(require_permission("patients.create")), facility_id: UUID = Depends(get_facility_context), db: Session = Depends(get_db)) -> PatientResponse:
    try:
        patient = create_patient(db, payload, actor_user_id=user.id, facility_id=facility_id)
    except ValueError as exc:
        code = str(exc)
        if code == "DUPLICATE_ID_NUMBER":
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail={"code": code, "message": "An AfyaSync patient already exists for this ID number."}) from exc
        if code == "INVALID_ID_NUMBER":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={"code": code, "message": "Enter a valid 7–9 digit national ID number."}) from exc
        if code == "DUPLICATE_PATIENT":
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail={"code": code, "message": "A possible existing patient was found."}) from exc
        if code == "FACILITY_CONTEXT_REQUIRED":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={"code": code, "message": "Select a facility before registering a patient."}) from exc
        if code == "IDENTITY_SEQUENCE_UNAVAILABLE":
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail={"code": code, "message": "Patient identity service is temporarily unavailable. Please try again."}) from exc
        if code == "PATIENT_CREATE_CONFLICT":
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail={"code": code, "message": "The patient record could not be created because it conflicts with an existing record. Refresh and try again."}) from exc
        raise
    return _response(patient)


@router.get("", response_model=PatientListResponse)
def list_patient_records(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    enrollment_status: Literal["ACTIVE", "INACTIVE"] | None = Query(default="ACTIVE"),
    scope: str = Query(default="facility", description="facility | network | county | national"),
    user: User = Depends(require_permission("patients.record.read")),
    facility_id: UUID = Depends(get_facility_context),
    db: Session = Depends(get_db),
) -> PatientListResponse:
    facility_ids = resolve_facility_ids(db, user=user, token_facility_id=facility_id, scope=scope)
    try:
        results, total = list_patients_for_facility(
            db, facility_id, limit=limit, offset=offset, enrollment_status=enrollment_status, facility_ids=facility_ids
        )
    except ValueError as exc:
        if str(exc) == "INVALID_ENROLLMENT_STATUS":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={"code": "INVALID_ENROLLMENT_STATUS", "message": "Enrollment status must be ACTIVE or INACTIVE."}) from exc
        raise
    record_audit(
        db,
        action="LIST_PATIENT_RECORDS",
        resource_type="PERSON",
        resource_id=str(facility_id),
        result="SUCCESS",
        user_id=user.id,
        facility_id=facility_id,
        metadata={
            "count": len(results),
            "total": total,
            "limit": limit,
            "offset": offset,
            "enrollment_status": enrollment_status,
            "scope": scope,
            "facility_count": len(facility_ids),
        },
        commit=True,
    )
    return PatientListResponse(items=[_response(person, identity.afya_id) for person, identity in results], total=total, limit=limit, offset=offset)


@router.get("/search", response_model=list[PatientSearchResult])
def search_patient_records(
    q: str = Query(min_length=2, max_length=100),
    limit: int = Query(default=20, ge=1, le=50),
    scope: str = Query(default="facility", description="facility | network | county | national"),
    user: User = Depends(require_permission("patients.search")),
    facility_id: UUID = Depends(get_facility_context),
    db: Session = Depends(get_db),
) -> list[PatientSearchResult]:
    facility_ids = resolve_facility_ids(db, user=user, token_facility_id=facility_id, scope=scope)
    results = search_patients(db, q, facility_id, limit, facility_ids=facility_ids)
    record_audit(
        db,
        action="SEARCH_PATIENT_RECORDS",
        resource_type="PERSON",
        resource_id=str(facility_id),
        result="SUCCESS",
        user_id=user.id,
        facility_id=facility_id,
        metadata={"result_count": len(results), "limit": limit, "scope": scope, "facility_count": len(facility_ids)},
        commit=True,
    )
    return [PatientSearchResult(id=person.id, afya_id=identity.afya_id, full_name=" ".join(filter(None, [person.first_name, person.middle_name, person.last_name])), phone=person.phone, status=person.status) for person, identity in results]


@router.get("/{patient_id}", response_model=PatientResponse)
def get_patient_record(patient_id: UUID, user: User = Depends(require_permission("patients.record.read")), facility_id: UUID = Depends(get_facility_context), db: Session = Depends(get_db)) -> PatientResponse:
    patient = get_patient_for_facility(db, patient_id, facility_id)
    if patient is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"code": "PATIENT_NOT_FOUND", "message": "Patient record not found."})
    record_audit(db, action="VIEW_PATIENT_RECORD", resource_type="PERSON", resource_id=str(patient.id), result="SUCCESS", user_id=user.id, facility_id=facility_id, patient_id=patient.id, commit=True)
    return _response(patient)


@router.get("/{patient_id}/encounters", response_model=EncounterListResponse)
def list_patient_encounter_timeline(patient_id: UUID, limit: int = Query(default=50, ge=1, le=100), offset: int = Query(default=0, ge=0), user: User = Depends(require_permission("clinical.record.read")), facility_id: UUID = Depends(get_facility_context), db: Session = Depends(get_db)) -> EncounterListResponse:
    try:
        items, total = list_patient_encounters_for_facility(db, patient_id, facility_id, limit=limit, offset=offset)
    except ValueError as exc:
        if str(exc) == "PATIENT_NOT_IN_FACILITY":
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"code": str(exc), "message": "Patient not enrolled at this facility."}) from exc
        raise
    record_audit(db, action="VIEW_PATIENT_ENCOUNTER_TIMELINE", resource_type="PERSON", resource_id=str(patient_id), result="SUCCESS", user_id=user.id, facility_id=facility_id, patient_id=patient_id, metadata={"count": len(items), "total": total}, commit=True)
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
        return enroll_patient_in_facility(db, patient_id, facility_id, actor_user_id=user.id)
    except ValueError as exc:
        code = str(exc)
        if code == "PATIENT_NOT_FOUND":
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"code": code, "message": "Patient record not found."}) from exc
        if code == "PATIENT_ALREADY_ENROLLED":
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail={"code": code, "message": "Patient is already enrolled at this facility."}) from exc
        raise


@router.patch("/{patient_id}/enrollment", response_model=PatientFacilityResponse)
def update_patient_enrollment(patient_id: UUID, payload: PatientFacilityStatusUpdate, user: User = Depends(require_permission("patients.record.write")), facility_id: UUID = Depends(get_facility_context), db: Session = Depends(get_db)) -> PatientFacilityResponse:
    try:
        return update_patient_facility_status(db, patient_id, facility_id, payload.status, actor_user_id=user.id)
    except ValueError as exc:
        code = str(exc)
        if code == "PATIENT_NOT_IN_FACILITY":
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"code": code, "message": "Enrollment status not found."}) from exc
        if code == "INVALID_PATIENT_FACILITY_STATUS":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={"code": code, "message": "Enrollment status must be ACTIVE or INACTIVE."}) from exc
        if code == "PATIENT_FACILITY_STATUS_UNCHANGED":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={"code": code, "message": "Enrollment status is already set to the requested value."}) from exc
        raise


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


@router.get("/{patient_id}/summary", response_model=PatientRecordSummaryResponse)
def get_complete_patient_record(patient_id: UUID, user: User = Depends(require_permission("patients.record.read")), facility_id: UUID = Depends(get_facility_context), db: Session = Depends(get_db)) -> PatientRecordSummaryResponse:
    try:
        record = get_patient_record_summary(db, patient_id, facility_id)
        if record is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"code": "PATIENT_NOT_FOUND", "message": "Patient record not found at this facility."})
        validated = PatientRecordSummaryResponse.model_validate(record)
        record_audit(db, action="VIEW_COMPLETE_PATIENT_RECORD", resource_type="PERSON", resource_id=str(patient_id), result="SUCCESS", user_id=user.id, facility_id=facility_id, patient_id=patient_id, metadata={"sections": ["identity", "coverage", "encounters", "laboratory", "prescriptions", "medication_actions", "admissions", "preauthorizations", "billing", "claims", "appointments", "queue", "referrals", "transfers"]}, commit=True)
        return validated
    except HTTPException:
        raise
    except Exception:
        fallback = _degraded_patient_record(db, patient_id, facility_id)
        if fallback is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"code": "PATIENT_NOT_FOUND", "message": "Patient record not found at this facility."})
        validated = PatientRecordSummaryResponse.model_validate(fallback)
        try:
            record_audit(db, action="VIEW_COMPLETE_PATIENT_RECORD_DEGRADED", resource_type="PERSON", resource_id=str(patient_id), result="SUCCESS", user_id=user.id, facility_id=facility_id, patient_id=patient_id, metadata={"degraded": True, "sections": ["identity", "encounters"]}, commit=True)
        except Exception:
            db.rollback()
        return validated
