"""API routes for SHA Treat Abroad — hardened + return-home package."""

from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user, require_facility_context, require_patient_identity
from app.database import get_db
from app.portal.service import PortalError, require_patient_person_id
from app.rbac.models import Staff, User
from app.treat_abroad.return_service import (
    get_package_for_case,
    issue_package,
    upsert_draft_package,
)
from app.treat_abroad.schemas import (
    ApprovedProcedureOut,
    OverseasCaseCreate,
    OverseasCaseOut,
    OverseasCaseUpdate,
)
from app.treat_abroad.seed import seed_approved_procedures
from app.treat_abroad.service import (
    create_case,
    get_case,
    list_approved_procedures,
    list_cases,
    update_case,
)

router = APIRouter(prefix="/api/v1/treat-abroad", tags=["Treat Abroad"])


class ReturnPackageIn(BaseModel):
    discharge_summary: str = Field(min_length=30, max_length=8000)
    procedures_performed: str = Field(min_length=10, max_length=4000)
    medications_on_discharge: str = Field(min_length=5, max_length=4000)
    follow_up_plan: str = Field(min_length=20, max_length=4000)
    complications: str | None = Field(default=None, max_length=4000)
    foreign_report_refs: str | None = Field(default=None, max_length=4000)
    follow_up_facility_id: UUID | None = None
    recommended_follow_up_date: date | None = None
    rehab_required: bool = False
    rehab_notes: str | None = Field(default=None, max_length=2000)


def _staff_for_user(db: Session, user: User, facility_id: UUID) -> UUID:
    if user.person_id is None:
        raise HTTPException(status_code=403, detail="STAFF_PROFILE_REQUIRED")
    staff = db.scalar(
        select(Staff).where(
            Staff.person_id == user.person_id,
            Staff.facility_id == facility_id,
            Staff.status == "ACTIVE",
        )
    )
    if staff is None:
        raise HTTPException(status_code=403, detail="STAFF_NOT_AT_FACILITY")
    return staff.id


def _map_create_error(code: str) -> int:
    if code in {"PATIENT_NOT_FOUND", "PROCEDURE_NOT_FOUND_OR_INACTIVE"}:
        return status.HTTP_404_NOT_FOUND
    if code == "TOO_MANY_OPEN_CASES":
        return status.HTTP_409_CONFLICT
    return status.HTTP_400_BAD_REQUEST


def _package_out(pkg) -> dict:
    return {
        "id": str(pkg.id),
        "case_id": str(pkg.case_id),
        "status": pkg.status,
        "discharge_summary": pkg.discharge_summary,
        "procedures_performed": pkg.procedures_performed,
        "medications_on_discharge": pkg.medications_on_discharge,
        "complications": pkg.complications,
        "foreign_report_refs": pkg.foreign_report_refs,
        "follow_up_plan": pkg.follow_up_plan,
        "follow_up_facility_id": str(pkg.follow_up_facility_id) if pkg.follow_up_facility_id else None,
        "recommended_follow_up_date": pkg.recommended_follow_up_date,
        "rehab_required": pkg.rehab_required,
        "rehab_notes": pkg.rehab_notes,
        "issued_at": pkg.issued_at,
        "created_at": pkg.created_at,
    }


@router.get("/procedures", response_model=list[ApprovedProcedureOut])
def get_approved_procedures(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    facility_id: UUID = Depends(require_facility_context),
):
    _ = facility_id
    rows = list_approved_procedures(db, active_only=True)
    if not rows:
        seed_approved_procedures(db)
        db.commit()
        rows = list_approved_procedures(db, active_only=True)
    return rows


@router.post("/cases", response_model=OverseasCaseOut, status_code=status.HTTP_201_CREATED)
def create_overseas_case(
    payload: OverseasCaseCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    facility_id: UUID = Depends(require_facility_context),
):
    if payload.facility_id != facility_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="FACILITY_MISMATCH")
    clinician_id = _staff_for_user(db, current_user, facility_id)
    data = payload.model_copy(update={"referring_clinician_id": clinician_id})
    try:
        case = create_case(db, payload=data, created_by=current_user.id)
        db.commit()
        db.refresh(case)
        return case
    except ValueError as exc:
        code = str(exc)
        raise HTTPException(status_code=_map_create_error(code), detail=code) from exc


@router.get("/cases", response_model=list[OverseasCaseOut])
def list_overseas_cases(
    patient_id: UUID | None = Query(default=None),
    status_filter: str | None = Query(default=None, alias="status"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    facility_id: UUID = Depends(require_facility_context),
):
    return list_cases(
        db, facility_id=facility_id, patient_id=patient_id, status=status_filter
    )


@router.get("/cases/{case_id}", response_model=OverseasCaseOut)
def get_overseas_case(
    case_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    facility_id: UUID = Depends(require_facility_context),
):
    try:
        return get_case(db, case_id, facility_id=facility_id)
    except ValueError as exc:
        code = str(exc)
        status_code = (
            status.HTTP_404_NOT_FOUND if code == "CASE_NOT_FOUND" else status.HTTP_403_FORBIDDEN
        )
        raise HTTPException(status_code=status_code, detail=code) from exc


@router.patch("/cases/{case_id}", response_model=OverseasCaseOut)
def patch_overseas_case(
    case_id: UUID,
    payload: OverseasCaseUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    facility_id: UUID = Depends(require_facility_context),
):
    try:
        case = get_case(db, case_id, facility_id=facility_id)
        updated = update_case(db, case=case, payload=payload, actor_user_id=current_user.id)
        db.commit()
        db.refresh(updated)
        return updated
    except ValueError as exc:
        detail = str(exc)
        if detail.startswith("INVALID_STATUS_TRANSITION") or detail in {
            "CASE_CLOSED",
            "RETURN_PACKAGE_REQUIRED",
        }:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detail) from exc
        if detail == "CASE_NOT_FOUND":
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail) from exc
        if detail == "FACILITY_ACCESS_DENIED":
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=detail) from exc
        if detail in {"AMOUNT_EXCEEDS_PROCEDURE_CAP", "INVALID_AMOUNT"}:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail) from exc
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail) from exc


@router.get("/cases/{case_id}/return-package")
def get_return_package(
    case_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    facility_id: UUID = Depends(require_facility_context),
):
    try:
        case = get_case(db, case_id, facility_id=facility_id)
    except ValueError as exc:
        code = str(exc)
        raise HTTPException(
            status_code=404 if code == "CASE_NOT_FOUND" else 403, detail=code
        ) from exc
    pkg = get_package_for_case(db, case.id)
    if pkg is None:
        raise HTTPException(status_code=404, detail="PACKAGE_NOT_FOUND")
    return _package_out(pkg)


@router.put("/cases/{case_id}/return-package")
def save_return_package(
    case_id: UUID,
    payload: ReturnPackageIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    facility_id: UUID = Depends(require_facility_context),
):
    _staff_for_user(db, current_user, facility_id)
    try:
        case = get_case(db, case_id, facility_id=facility_id)
        pkg = upsert_draft_package(
            db,
            case=case,
            actor_user_id=current_user.id,
            discharge_summary=payload.discharge_summary,
            procedures_performed=payload.procedures_performed,
            medications_on_discharge=payload.medications_on_discharge,
            follow_up_plan=payload.follow_up_plan,
            complications=payload.complications,
            foreign_report_refs=payload.foreign_report_refs,
            follow_up_facility_id=payload.follow_up_facility_id,
            recommended_follow_up_date=payload.recommended_follow_up_date,
            rehab_required=payload.rehab_required,
            rehab_notes=payload.rehab_notes,
        )
        db.commit()
        db.refresh(pkg)
        return _package_out(pkg)
    except ValueError as exc:
        detail = str(exc)
        code = 409 if detail in {"PACKAGE_ALREADY_ISSUED", "CASE_NOT_ELIGIBLE_FOR_RETURN_PACKAGE"} else 400
        raise HTTPException(status_code=code, detail=detail) from exp if False else HTTPException(
            status_code=code, detail=detail
        ) from exc


@router.post("/cases/{case_id}/return-package/issue")
def issue_return_package(
    case_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    facility_id: UUID = Depends(require_facility_context),
):
    _staff_for_user(db, current_user, facility_id)
    try:
        case = get_case(db, case_id, facility_id=facility_id)
        pkg = issue_package(db, case=case, actor_user_id=current_user.id)
        db.commit()
        db.refresh(pkg)
        return _package_out(pkg)
    except ValueError as exc:
        detail = str(exc)
        code = 409 if detail in {
            "PACKAGE_REQUIRED",
            "CASE_NOT_ELIGIBLE_FOR_RETURN_PACKAGE",
            "PACKAGE_ALREADY_ISSUED",
        } else 400
        raise HTTPException(status_code=code, detail=detail) from exc


@router.get("/portal/return-packages")
def portal_return_packages(
    db: Session = Depends(get_db),
    user: User = Depends(require_patient_identity),
):
    """Patient sees issued packages only (continuity of care)."""
    try:
        person_id = require_patient_person_id(user.person_id)
    except PortalError as err:
        raise HTTPException(status_code=403, detail=str(err)) from err
    cases = list_cases(db, patient_id=person_id)
    out = []
    for c in cases:
        pkg = get_package_for_case(db, c.id)
        if pkg and pkg.status == "ISSUED":
            out.append(
                {
                    "case_number": c.case_number,
                    "case_status": c.status,
                    "package": _package_out(pkg),
                }
            )
    return out
