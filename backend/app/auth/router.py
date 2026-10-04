from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit.service import record_audit
from app.auth.dependencies import get_current_user, get_token_payload
from app.auth.rate_limit import enforce_auth_rate_limit
from app.auth.schemas import FacilityOption, FacilitySelectionRequest, FacilitySelectionRequired, GovernmentOrganizationOption, GovernmentSelectionRequired, LoginRequest, RefreshTokenRequest, TokenResponse
from app.auth.service import authenticate_user, issue_access_token, issue_refresh_token, revoke_refresh_token, rotate_tokens_from_refresh
from app.config import settings
from app.database import get_db
from app.facilities.models import Facility
from app.rbac.models import Role, Staff, StaffRole, User
from app.tenancy.models import GovernmentAccess, Organization

router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])


def _client_ip(request: Request) -> str | None:
    return request.client.host if request.client else None


def _token_response(db: Session, user: User, facility_id, portal_type: str = "facility", organization_id=None) -> TokenResponse:
    return TokenResponse(
        access_token=issue_access_token(user, facility_id, portal_type=portal_type, organization_id=organization_id),
        refresh_token=issue_refresh_token(db, user, facility_id, portal_type=portal_type, organization_id=organization_id),
        expires_in=settings.access_token_minutes * 60,
    )


def _is_system_administrator(db: Session, user: User) -> bool:
    if not isinstance(user, User) or user.person_id is None:
        return False
    return db.scalar(
        select(StaffRole.staff_id)
        .join(Staff, Staff.id == StaffRole.staff_id)
        .join(Role, Role.id == StaffRole.role_id)
        .where(Staff.person_id == user.person_id, Staff.status == "ACTIVE", Role.name == "System Administrator")
        .limit(1)
    ) is not None


def _facility_options(db: Session, user: User, all_active: bool = False) -> list[FacilityOption]:
    if all_active:
        rows = db.execute(select(Facility.id, Facility.name).where(Facility.status == "ACTIVE").order_by(Facility.name)).all()
    else:
        rows = db.execute(
            select(Facility.id, Facility.name)
            .join(Staff, Staff.facility_id == Facility.id)
            .where(Staff.person_id == user.person_id, Staff.status == "ACTIVE", Facility.status == "ACTIVE")
            .distinct()
            .order_by(Facility.name)
        ).all()
    return [FacilityOption(facility_id=row[0], facility_name=row[1]) for row in rows]


@router.post("/login", response_model=TokenResponse | FacilitySelectionRequired)
def login(payload: LoginRequest, request: Request, db: Session = Depends(get_db), _: None = Depends(enforce_auth_rate_limit)) -> TokenResponse | FacilitySelectionRequired:
    result = authenticate_user(db, payload.username, payload.password)
    if result is None:
        record_audit(db, action="AUTH_LOGIN", resource_type="USER", result="FAILURE", ip_address=_client_ip(request), metadata={"username": payload.username})
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="INVALID_CREDENTIALS", headers={"WWW-Authenticate": "Bearer"})
    user, staff = result
    system_admin = _is_system_administrator(db, user)
    if len(staff) == 0 and not system_admin:
        record_audit(db, action="AUTH_LOGIN", resource_type="USER", result="NO_ACTIVE_FACILITY_ASSIGNMENT", user_id=user.id, ip_address=_client_ip(request))
        raise HTTPException(status_code=403, detail="NO_ACTIVE_FACILITY_ASSIGNMENT")

    # A non-administrator with one assigned active facility does not need a
    # database directory lookup merely to establish the same unambiguous scope.
    if len(staff) == 1 and not system_admin:
        facility_id = staff[0].facility_id
        record_audit(db, action="AUTH_LOGIN", resource_type="USER", result="SUCCESS", user_id=user.id, facility_id=facility_id, ip_address=_client_ip(request))
        return _token_response(db, user, facility_id)

    options = _facility_options(db, user, all_active=system_admin)
    if not options:
        record_audit(db, action="AUTH_LOGIN", resource_type="USER", result="NO_ACTIVE_FACILITIES", user_id=user.id, ip_address=_client_ip(request))
        raise HTTPException(status_code=403, detail="NO_ACTIVE_FACILITIES")

    record_audit(db, action="AUTH_LOGIN", resource_type="USER", result="FACILITY_SELECTION_REQUIRED", user_id=user.id, ip_address=_client_ip(request))
    return FacilitySelectionRequired(access_token=issue_access_token(user, None), facilities=options)


@router.post("/government/login", response_model=TokenResponse | GovernmentSelectionRequired)
def government_login(payload: LoginRequest, request: Request, db: Session = Depends(get_db), _: None = Depends(enforce_auth_rate_limit)):
    result = authenticate_user(db, payload.username, payload.password)
    if result is None:
        record_audit(db, action="GOV_AUTH_LOGIN", resource_type="USER", result="FAILURE", ip_address=_client_ip(request), metadata={"username": payload.username})
        raise HTTPException(status_code=401, detail="INVALID_CREDENTIALS", headers={"WWW-Authenticate": "Bearer"})
    user, _ = result
    rows = list(db.execute(
        select(GovernmentAccess, Organization)
        .join(Organization, Organization.id == GovernmentAccess.organization_id)
        .where(GovernmentAccess.user_id == user.id, GovernmentAccess.status == "ACTIVE", Organization.status == "ACTIVE", Organization.organization_type.in_(["COUNTY_GOVERNMENT", "NATIONAL_GOVERNMENT"]))
        .order_by(Organization.organization_type, Organization.name)
    ).all())
    if not rows:
        record_audit(db, action="GOV_AUTH_LOGIN", resource_type="USER", result="NO_GOVERNMENT_ACCESS", user_id=user.id, ip_address=_client_ip(request))
        raise HTTPException(status_code=403, detail="NO_GOVERNMENT_ACCESS")
    if len(rows) == 1:
        access, org = rows[0]
        record_audit(db, action="GOV_AUTH_LOGIN", resource_type="ORGANIZATION", resource_id=str(org.id), result="SUCCESS", user_id=user.id, ip_address=_client_ip(request), metadata={"scope_level": access.scope_level, "role_code": access.role_code})
        return _token_response(db, user, None, portal_type="government", organization_id=org.id)
    return GovernmentSelectionRequired(
        access_token=issue_access_token(user, None, portal_type="government"),
        organizations=[GovernmentOrganizationOption(organization_id=org.id, organization_name=org.name, organization_type=org.organization_type, scope_level=access.scope_level, role_code=access.role_code) for access, org in rows],
    )


@router.get("/government/organizations", response_model=list[GovernmentOrganizationOption])
def government_organizations(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = list(db.execute(
        select(GovernmentAccess, Organization)
        .join(Organization, Organization.id == GovernmentAccess.organization_id)
        .where(GovernmentAccess.user_id == user.id, GovernmentAccess.status == "ACTIVE", Organization.status == "ACTIVE")
        .order_by(Organization.organization_type, Organization.name)
    ).all())
    return [GovernmentOrganizationOption(organization_id=org.id, organization_name=org.name, organization_type=org.organization_type, scope_level=access.scope_level, role_code=access.role_code) for access, org in rows]


@router.post("/government/select-organization", response_model=TokenResponse)
def select_government_organization(organization_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    from uuid import UUID
    try:
        org_id = UUID(organization_id)
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail="INVALID_GOVERNMENT_ORGANIZATION")
    row = db.execute(
        select(GovernmentAccess, Organization)
        .join(Organization, Organization.id == GovernmentAccess.organization_id)
        .where(GovernmentAccess.user_id == user.id, GovernmentAccess.organization_id == org_id, GovernmentAccess.status == "ACTIVE", Organization.status == "ACTIVE")
    ).first()
    if row is None:
        raise HTTPException(status_code=403, detail="GOVERNMENT_ORGANIZATION_ACCESS_DENIED")
    access, org = row
    if org.organization_type not in ("COUNTY_GOVERNMENT", "NATIONAL_GOVERNMENT"):
        raise HTTPException(status_code=403, detail="NOT_A_GOVERNMENT_ORGANIZATION")
    record_audit(db, action="GOV_AUTH_ORGANIZATION_SELECT", resource_type="ORGANIZATION", resource_id=str(org.id), result="SUCCESS", user_id=user.id, metadata={"scope_level": access.scope_level, "role_code": access.role_code})
    return _token_response(db, user, None, portal_type="government", organization_id=org.id)


@router.get("/government/me")
def government_me(user: User = Depends(get_current_user), payload: dict = Depends(get_token_payload), db: Session = Depends(get_db)):
    from uuid import UUID
    if payload.get("portal_type") != "government" or not payload.get("organization_id"):
        raise HTTPException(status_code=403, detail="GOVERNMENT_PORTAL_TOKEN_REQUIRED")
    try:
        org_id = UUID(payload["organization_id"])
    except (ValueError, TypeError):
        raise HTTPException(status_code=403, detail="INVALID_GOVERNMENT_CONTEXT")
    row = db.execute(
        select(GovernmentAccess, Organization)
        .join(Organization, Organization.id == GovernmentAccess.organization_id)
        .where(GovernmentAccess.user_id == user.id, GovernmentAccess.organization_id == org_id, GovernmentAccess.status == "ACTIVE", Organization.status == "ACTIVE")
    ).first()
    if row is None:
        raise HTTPException(status_code=403, detail="GOVERNMENT_ACCESS_REVOKED")
    access, org = row
    return {"success": True, "data": {"user_id": str(user.id), "username": user.username, "portal_type": "government", "organization_id": str(org.id), "organization_name": org.name, "organization_type": org.organization_type, "scope_level": access.scope_level, "role_code": access.role_code}}


@router.post("/refresh", response_model=TokenResponse)
def refresh(payload: RefreshTokenRequest, request: Request, db: Session = Depends(get_db), _: None = Depends(enforce_auth_rate_limit)) -> TokenResponse:
    try:
        result = rotate_tokens_from_refresh(db, payload.refresh_token)
    except HTTPException:
        result = None
    if result is None:
        record_audit(db, action="AUTH_REFRESH", resource_type="USER", result="FAILURE", ip_address=_client_ip(request))
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="INVALID_REFRESH_TOKEN", headers={"WWW-Authenticate": "Bearer"})
    user, facility_id, new_refresh_token = result
    record_audit(db, action="AUTH_REFRESH", resource_type="USER", result="SUCCESS", user_id=user.id, facility_id=facility_id, ip_address=_client_ip(request))
    return TokenResponse(access_token=issue_access_token(user, facility_id), refresh_token=new_refresh_token, expires_in=settings.access_token_minutes * 60)


@router.post("/logout")
def logout(payload: RefreshTokenRequest, request: Request, db: Session = Depends(get_db)) -> dict[str, object]:
    revoked = revoke_refresh_token(db, payload.refresh_token)
    if not revoked:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="INVALID_REFRESH_TOKEN")
    record_audit(db, action="AUTH_LOGOUT", resource_type="REFRESH_SESSION", result="SUCCESS", ip_address=_client_ip(request))
    return {"success": True, "data": {"revoked": True}, "message": "Session revoked"}


@router.get("/facilities", response_model=list[FacilityOption])
def facilities(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[FacilityOption]:
    return _facility_options(db, user, all_active=_is_system_administrator(db, user))


@router.post("/select-facility", response_model=TokenResponse)
def select_facility(payload: FacilitySelectionRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> TokenResponse:
    facility = db.get(Facility, payload.facility_id)
    system_admin = _is_system_administrator(db, user)
    staff = None if system_admin else db.scalar(select(Staff).where(Staff.person_id == user.person_id, Staff.facility_id == payload.facility_id, Staff.status == "ACTIVE"))
    if facility is None or facility.status != "ACTIVE" or (not system_admin and staff is None):
        record_audit(db, action="AUTH_FACILITY_SELECT", resource_type="FACILITY", result="FAILURE", user_id=user.id, facility_id=payload.facility_id)
        raise HTTPException(status_code=403, detail="FACILITY_ACCESS_DENIED")
    record_audit(db, action="AUTH_FACILITY_SELECT", resource_type="FACILITY", result="SUCCESS", user_id=user.id, facility_id=payload.facility_id)
    return _token_response(db, user, payload.facility_id)


@router.get("/me")
def me(user: User = Depends(get_current_user)) -> dict[str, object]:
    return {"success": True, "data": {"user_id": str(user.id), "username": user.username, "status": user.status}, "message": "Authenticated user"}
