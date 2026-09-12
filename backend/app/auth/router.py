from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit.service import record_audit
from app.auth.dependencies import get_current_user
from app.auth.schemas import (
    FacilityOption,
    FacilitySelectionRequest,
    FacilitySelectionRequired,
    LoginRequest,
    RefreshTokenRequest,
    TokenResponse,
)
from app.auth.service import authenticate_user, issue_access_token, issue_refresh_token, revoke_refresh_token, rotate_tokens_from_refresh
from app.config import settings
from app.database import get_db
from app.facilities.models import Facility
from app.rbac.models import Staff, User

router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])


def _client_ip(request: Request) -> str | None:
    return request.client.host if request.client else None


def _token_response(db: Session, user: User, facility_id) -> TokenResponse:
    return TokenResponse(
        access_token=issue_access_token(user, facility_id),
        refresh_token=issue_refresh_token(db, user, facility_id),
        expires_in=settings.access_token_minutes * 60,
    )


@router.post("/login", response_model=TokenResponse | FacilitySelectionRequired)
def login(payload: LoginRequest, request: Request, db: Session = Depends(get_db)) -> TokenResponse | FacilitySelectionRequired:
    result = authenticate_user(db, payload.username, payload.password)
    if result is None:
        record_audit(
            db,
            action="AUTH_LOGIN",
            resource_type="USER",
            result="FAILURE",
            ip_address=_client_ip(request),
            metadata={"username": payload.username},
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="INVALID_CREDENTIALS",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user, staff = result
    if len(staff) == 0:
        record_audit(
            db,
            action="AUTH_LOGIN",
            resource_type="USER",
            result="NO_ACTIVE_FACILITY_ASSIGNMENT",
            user_id=user.id,
            ip_address=_client_ip(request),
        )
        raise HTTPException(status_code=403, detail="NO_ACTIVE_FACILITY_ASSIGNMENT")
    if len(staff) != 1:
        # More than one active facility: issue a facility-scope-less access
        # token (valid for get_current_user, rejected by get_facility_context
        # on every facility-scoped endpoint) so the client can call
        # /auth/select-facility to exchange it for a fully scoped
        # TokenResponse. No refresh token yet — a refresh session is only
        # created once a facility is actually selected.
        rows = db.execute(
            select(Facility.id, Facility.name)
            .join(Staff, Staff.facility_id == Facility.id)
            .where(
                Staff.person_id == user.person_id,
                Staff.status == "ACTIVE",
                Facility.status == "ACTIVE",
            )
            .distinct()
        ).all()
        record_audit(
            db,
            action="AUTH_LOGIN",
            resource_type="USER",
            result="FACILITY_SELECTION_REQUIRED",
            user_id=user.id,
            ip_address=_client_ip(request),
        )
        return FacilitySelectionRequired(
            access_token=issue_access_token(user, None),
            facilities=[FacilityOption(facility_id=row[0], facility_name=row[1]) for row in rows],
        )
    facility_id = staff[0].facility_id
    record_audit(
        db,
        action="AUTH_LOGIN",
        resource_type="USER",
        result="SUCCESS",
        user_id=user.id,
        facility_id=facility_id,
        ip_address=_client_ip(request),
    )
    return _token_response(db, user, facility_id)


@router.post("/refresh", response_model=TokenResponse)
def refresh(
    payload: RefreshTokenRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> TokenResponse:
    try:
        result = rotate_tokens_from_refresh(db, payload.refresh_token)
    except HTTPException:
        result = None
    if result is None:
        record_audit(
            db,
            action="AUTH_REFRESH",
            resource_type="USER",
            result="FAILURE",
            ip_address=_client_ip(request),
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="INVALID_REFRESH_TOKEN",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user, facility_id, new_refresh_token = result
    record_audit(
        db,
        action="AUTH_REFRESH",
        resource_type="USER",
        result="SUCCESS",
        user_id=user.id,
        facility_id=facility_id,
        ip_address=_client_ip(request),
    )
    return TokenResponse(
        access_token=issue_access_token(user, facility_id),
        refresh_token=new_refresh_token,
        expires_in=settings.access_token_minutes * 60,
    )


@router.post("/logout")
def logout(
    payload: RefreshTokenRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> dict[str, object]:
    revoked = revoke_refresh_token(db, payload.refresh_token)
    if not revoked:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="INVALID_REFRESH_TOKEN")
    record_audit(
        db,
        action="AUTH_LOGOUT",
        resource_type="REFRESH_SESSION",
        result="SUCCESS",
        ip_address=_client_ip(request),
    )
    return {"success": True, "data": {"revoked": True}, "message": "Session revoked"}


@router.get("/facilities", response_model=list[FacilityOption])
def facilities(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[FacilityOption]:
    rows = db.execute(
        select(Facility.id, Facility.name)
        .join(Staff, Staff.facility_id == Facility.id)
        .where(
            Staff.person_id == user.person_id,
            Staff.status == "ACTIVE",
            Facility.status == "ACTIVE",
        )
        .distinct()
    ).all()
    return [FacilityOption(facility_id=row[0], facility_name=row[1]) for row in rows]


@router.post("/select-facility", response_model=TokenResponse)
def select_facility(
    payload: FacilitySelectionRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TokenResponse:
    staff = db.scalar(
        select(Staff).where(
            Staff.person_id == user.person_id,
            Staff.facility_id == payload.facility_id,
            Staff.status == "ACTIVE",
        )
    )
    facility = db.get(Facility, payload.facility_id)
    if staff is None or facility is None or facility.status != "ACTIVE":
        record_audit(
            db,
            action="AUTH_FACILITY_SELECT",
            resource_type="FACILITY",
            result="FAILURE",
            user_id=user.id,
            facility_id=payload.facility_id,
        )
        raise HTTPException(status_code=403, detail="FACILITY_ACCESS_DENIED")
    record_audit(
        db,
        action="AUTH_FACILITY_SELECT",
        resource_type="FACILITY",
        result="SUCCESS",
        user_id=user.id,
        facility_id=payload.facility_id,
    )
    return _token_response(db, user, payload.facility_id)


@router.get("/me")
def me(user: User = Depends(get_current_user)) -> dict[str, object]:
    return {
        "success": True,
        "data": {"user_id": str(user.id), "username": user.username, "status": user.status},
        "message": "Authenticated user",
    }
