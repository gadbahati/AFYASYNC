"""Patient portal authentication endpoints."""

import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.auth.patient_schemas import (
    PatientAuthTokenResponse,
    PatientLoginRequest,
    PatientPasswordResetConfirm,
    PatientPasswordResetRequest,
    PatientPasswordResetRequested,
    PatientRegisterRequest,
)
from app.auth.patient_service import (
    confirm_password_reset,
    login_patient,
    register_patient,
    request_password_reset,
)
from app.auth.rate_limit import enforce_auth_rate_limit
from app.config import settings
from app.database import get_db

logger = logging.getLogger("afyasync.patient_auth")
router = APIRouter(prefix="/api/v1/auth/patient", tags=["Patient Authentication"])


def _ip(request: Request) -> str | None:
    return request.client.host if request.client else None


@router.post("/register", response_model=PatientAuthTokenResponse, status_code=status.HTTP_201_CREATED)
def patient_register(
    payload: PatientRegisterRequest,
    request: Request,
    db=Depends(get_db),
    _: None = Depends(enforce_auth_rate_limit),
):
    """Create a patient portal password for an existing Afya ID.

    The person must already be registered in the health system.
    """
    try:
        user = register_patient(db, payload=payload, ip_address=_ip(request))
        from app.auth.patient_schemas import PatientLoginRequest as _Login

        _user, access, refresh, expires = login_patient(
            db,
            payload=_Login(identifier=payload.afya_id, password=payload.password),
            ip_address=_ip(request),
        )
        db.commit()
        return PatientAuthTokenResponse(
            access_token=access,
            refresh_token=refresh,
            expires_in=expires,
        )
    except ValueError as exc:
        code = str(exc)
        mapping = {
            "AFYA_ID_NOT_FOUND": status.HTTP_404_NOT_FOUND,
            "ACCOUNT_ALREADY_EXISTS": status.HTTP_409_CONFLICT,
            "USERNAME_CONFLICT": status.HTTP_409_CONFLICT,
        }
        raise HTTPException(
            status_code=mapping.get(code, status.HTTP_400_BAD_REQUEST),
            detail=code,
        ) from exc


@router.post("/login", response_model=PatientAuthTokenResponse)
def patient_login(
    payload: PatientLoginRequest,
    request: Request,
    db=Depends(get_db),
    _: None = Depends(enforce_auth_rate_limit),
):
    """Sign in with Afya ID or SHA membership number and password."""
    try:
        _user, access, refresh, expires = login_patient(
            db, payload=payload, ip_address=_ip(request)
        )
        db.commit()
        return PatientAuthTokenResponse(
            access_token=access,
            refresh_token=refresh,
            expires_in=expires,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="INVALID_CREDENTIALS",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


@router.post("/password-reset/request", response_model=PatientPasswordResetRequested)
def patient_password_reset_request(
    payload: PatientPasswordResetRequest,
    request: Request,
    db=Depends(get_db),
    _: None = Depends(enforce_auth_rate_limit),
):
    """Request a one-time reset code sent to phone or email on file."""
    try:
        channel, hint, code = request_password_reset(
            db, payload=payload, ip_address=_ip(request)
        )
        db.commit()

        # Deliver code: in production plug SMS/email provider here.
        # Never return the code in the API response.
        if code and settings.environment != "production":
            logger.info(
                "Patient password reset code generated channel=%s dest=%s (non-prod only)",
                channel,
                hint,
            )
            # Ops may read from secure logs; code itself is not logged in full in production path

        if code and settings.environment == "production":
            # Placeholder for real SMS/email gateway integration
            logger.info("Patient password reset code queued for delivery channel=%s", channel)

        return PatientPasswordResetRequested(
            message=(
                "If an account exists for that identifier, a reset code has been sent."
            ),
            channel=channel,
            destination_hint=hint,
        )
    except ValueError as exc:
        code = str(exc)
        if code in {"NO_PHONE_ON_FILE", "NO_EMAIL_ON_FILE"}:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=code) from exc
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=code) from exc


@router.post("/password-reset/confirm")
def patient_password_reset_confirm(
    payload: PatientPasswordResetConfirm,
    request: Request,
    db=Depends(get_db),
    _: None = Depends(enforce_auth_rate_limit),
):
    """Confirm reset code and set a new password."""
    try:
        confirm_password_reset(db, payload=payload, ip_address=_ip(request))
        db.commit()
        return {
            "success": True,
            "message": "Password updated. You can now sign in.",
        }
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
