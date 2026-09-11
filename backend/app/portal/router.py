from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.database import get_db
from app.portal.schemas import (
    PortalEncounterListResponse,
    PortalEncounterSummary,
    PortalProfileResponse,
    PortalReferralListResponse,
)
from app.portal.service import (
    PortalError,
    audit_portal_view,
    get_my_encounter,
    get_my_encounter_summary,
    get_my_profile,
    list_my_encounters,
    list_my_referrals,
    require_patient_person_id,
)
from app.rbac.models import User

router = APIRouter(prefix="/api/v1/portal", tags=["Patient Portal"])


def _person_id(user: User) -> UUID:
    try:
        return require_patient_person_id(user.person_id)
    except PortalError as err:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(err)) from err


def _error(err: PortalError) -> HTTPException:
    code = str(err)
    mapping = {
        "PATIENT_IDENTITY_REQUIRED": 403,
        "PATIENT_NOT_FOUND": 404,
        "ENCOUNTER_NOT_FOUND": 404,
    }
    return HTTPException(status_code=mapping.get(code, 400), detail=code)


@router.get("/me", response_model=PortalProfileResponse)
def portal_profile(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PortalProfileResponse:
    person_id = _person_id(user)
    try:
        person, identity = get_my_profile(db, person_id)
    except PortalError as err:
        raise _error(err) from err

    audit_portal_view(
        db,
        user_id=user.id,
        person_id=person_id,
        action="PORTAL_VIEW_PROFILE",
        resource_type="PERSON",
        resource_id=str(person_id),
    )
    return PortalProfileResponse(
        id=person.id,
        afya_id=identity.afya_id if identity else None,
        first_name=person.first_name,
        middle_name=person.middle_name,
        last_name=person.last_name,
        date_of_birth=person.date_of_birth,
        sex=person.sex,
        phone=person.phone,
        email=person.email,
        status=person.status,
    )


@router.get("/encounters", response_model=PortalEncounterListResponse)
def portal_encounters(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PortalEncounterListResponse:
    person_id = _person_id(user)
    items, total = list_my_encounters(db, person_id, limit=limit, offset=offset)
    audit_portal_view(
        db,
        user_id=user.id,
        person_id=person_id,
        action="PORTAL_LIST_ENCOUNTERS",
        resource_type="PERSON",
        resource_id=str(person_id),
        metadata={"count": len(items), "total": total},
    )
    return PortalEncounterListResponse(items=items, total=total, limit=limit, offset=offset)


@router.get("/encounters/{encounter_id}", response_model=PortalEncounterSummary)
def portal_encounter_summary(
    encounter_id: UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PortalEncounterSummary:
    person_id = _person_id(user)
    try:
        summary = get_my_encounter_summary(db, person_id, encounter_id)
    except PortalError as err:
        raise _error(err) from err

    audit_portal_view(
        db,
        user_id=user.id,
        person_id=person_id,
        action="PORTAL_VIEW_ENCOUNTER_SUMMARY",
        resource_type="ENCOUNTER",
        resource_id=str(encounter_id),
    )
    return PortalEncounterSummary(
        encounter=summary["encounter"],
        vitals=summary["vitals"],
        consultation=summary["consultation"],
        diagnoses=summary["diagnoses"],
        lab_orders=summary["lab_orders"],
        prescriptions=summary["prescriptions"],
    )


@router.get("/referrals", response_model=PortalReferralListResponse)
def portal_referrals(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PortalReferralListResponse:
    person_id = _person_id(user)
    items, total = list_my_referrals(db, person_id, limit=limit, offset=offset)
    audit_portal_view(
        db,
        user_id=user.id,
        person_id=person_id,
        action="PORTAL_LIST_REFERRALS",
        resource_type="PERSON",
        resource_id=str(person_id),
        metadata={"count": len(items), "total": total},
    )
    return PortalReferralListResponse(items=items, total=total, limit=limit, offset=offset)
