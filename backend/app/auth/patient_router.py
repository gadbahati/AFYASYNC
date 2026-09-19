"""Patient portal authentication endpoints."""

import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status

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
from app.database import get_db
from app.notifications.delivery import deliver_password_reset_code

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
    try:
        register_patient(db, payload=payload, ip_address=_ip(request))
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
    """Request a one-time reset code sent to phone or email on file.

    The plain code is never returned in the API response.
    """
    try:
        channel, hint, code, destination = request_password_reset(
            db, payload=payload, ip_address=_ip(request)
        )
        db.commit()

        if code and destination:
            delivered = deliver_password_reset_code(
                channel=channel,
                destination=destination,
                code=code,
                destination_hint=hint,
            )
            if not delivered:
                logger.warning(
                    "Password reset code generated but delivery failed channel=%s dest=%s",
                    channel,
                    hint,
                )

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
