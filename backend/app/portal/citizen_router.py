"""Afya Citizen super-portal routes."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.auth.dependencies import require_patient_identity
from app.database import get_db
from app.portal.citizen_schemas import (
    AccessHistoryResponse,
    ChargeExplainResponse,
    ComplaintCreate,
    ComplaintListResponse,
    DocumentListResponse,
    EmergencySummary,
    TimelineResponse,
)
from app.portal.citizen_service import (
    create_complaint,
    explain_my_charges,
    get_access_history,
    get_emergency_summary,
    get_health_timeline,
    list_complaints,
    list_my_documents,
)
from app.portal.service import PortalError, audit_portal_view, require_patient_person_id
from app.rbac.models import User

router = APIRouter(prefix="/api/v1/portal/citizen", tags=["Afya Citizen"])


def _person_id(user: User) -> UUID:
    try:
        return require_patient_person_id(user.person_id)
    except PortalError as err:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(err)) from err


def _err(err: PortalError) -> HTTPException:
    code = str(err)
    mapping = {"PATIENT_NOT_FOUND": 404, "PATIENT_IDENTITY_REQUIRED": 403}
    return HTTPException(status_code=mapping.get(code, 400), detail=code)


@router.get("/timeline", response_model=TimelineResponse)
def citizen_timeline(
    limit: int = Query(default=50, ge=1, le=100),
    user: User = Depends(require_patient_identity),
    db: Session = Depends(get_db),
) -> TimelineResponse:
    person_id = _person_id(user)
    try:
        result = get_health_timeline(db, person_id, limit=limit)
    except PortalError as e:
        raise _err(e) from e
    audit_portal_view(
        db,
        user_id=user.id,
        person_id=person_id,
        action="PORTAL_VIEW_TIMELINE",
        resource_type="PERSON",
        resource_id=str(person_id),
    )
    return result


@router.get("/access-history", response_model=AccessHistoryResponse)
def citizen_access_history(
    limit: int = Query(default=50, ge=1, le=100),
    user: User = Depends(require_patient_identity),
    db: Session = Depends(get_db),
) -> AccessHistoryResponse:
    person_id = _person_id(user)
    try:
        result = get_access_history(db, person_id, limit=limit)
    except PortalError as e:
        raise _err(e) from e
    audit_portal_view(
        db,
        user_id=user.id,
        person_id=person_id,
        action="PORTAL_VIEW_ACCESS_HISTORY",
        resource_type="PERSON",
        resource_id=str(person_id),
    )
    return result


@router.get("/charges", response_model=ChargeExplainResponse)
def citizen_charges(
    limit: int = Query(default=50, ge=1, le=100),
    user: User = Depends(require_patient_identity),
    db: Session = Depends(get_db),
) -> ChargeExplainResponse:
    person_id = _person_id(user)
    try:
        result = explain_my_charges(db, person_id, limit=limit)
    except PortalError as e:
        raise _err(e) from e
    audit_portal_view(
        db,
        user_id=user.id,
        person_id=person_id,
        action="PORTAL_VIEW_CHARGES",
        resource_type="PERSON",
        resource_id=str(person_id),
    )
    return result


@router.get("/emergency-summary", response_model=EmergencySummary)
def citizen_emergency(
    user: User = Depends(require_patient_identity),
    db: Session = Depends(get_db),
) -> EmergencySummary:
    person_id = _person_id(user)
    try:
        result = get_emergency_summary(db, person_id)
    except PortalError as e:
        raise _err(e) from e
    audit_portal_view(
        db,
        user_id=user.id,
        person_id=person_id,
        action="PORTAL_VIEW_EMERGENCY_SUMMARY",
        resource_type="PERSON",
        resource_id=str(person_id),
    )
    return result


@router.get("/documents", response_model=DocumentListResponse)
def citizen_documents(
    user: User = Depends(require_patient_identity),
    db: Session = Depends(get_db),
) -> DocumentListResponse:
    person_id = _person_id(user)
    result = list_my_documents(db, person_id)
    audit_portal_view(
        db,
        user_id=user.id,
        person_id=person_id,
        action="PORTAL_VIEW_DOCUMENTS",
        resource_type="PERSON",
        resource_id=str(person_id),
    )
    return result


@router.get("/complaints", response_model=ComplaintListResponse)
def citizen_list_complaints(
    user: User = Depends(require_patient_identity),
    db: Session = Depends(get_db),
) -> ComplaintListResponse:
    person_id = _person_id(user)
    return list_complaints(db, person_id)


@router.post("/complaints", status_code=status.HTTP_201_CREATED)
def citizen_create_complaint(
    payload: ComplaintCreate,
    user: User = Depends(require_patient_identity),
    db: Session = Depends(get_db),
):
    person_id = _person_id(user)
    try:
        row = create_complaint(
            db, person_id=person_id, payload=payload, actor_user_id=user.id
        )
        db.commit()
        return {"id": str(row.id), "status": row.status, "category": row.category}
    except PortalError as e:
        raise _err(e) from e
