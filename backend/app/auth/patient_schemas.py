"""Schemas for patient registration, login, and password reset."""

from pydantic import BaseModel, Field


class PatientRegisterRequest(BaseModel):
    """Create a patient portal account linked to an existing Afya identity.

    The person must already exist in the system (registered at a facility)
    with an Afya ID. Registration only sets the portal password.
    """

    afya_id: str = Field(min_length=3, max_length=40, description="AfyaSync ID")
    password: str = Field(min_length=8, max_length=128)
    phone: str | None = Field(default=None, max_length=30)
    email: str | None = Field(default=None, max_length=320)


class PatientLoginRequest(BaseModel):
    """Sign in with Afya ID or SHA membership number + password."""

    identifier: str = Field(
        min_length=3,
        max_length=100,
        description="Afya ID or SHA membership number",
    )
    password: str = Field(min_length=1, max_length=128)


class PatientPasswordResetRequest(BaseModel):
    identifier: str = Field(
        min_length=3,
        max_length=100,
        description="Afya ID or SHA membership number",
    )
    channel: str = Field(
        default="PHONE",
        pattern="^(PHONE|EMAIL)$",
        description="Where to send the reset code",
    )


class PatientPasswordResetConfirm(BaseModel):
    identifier: str = Field(min_length=3, max_length=100)
    code: str = Field(min_length=4, max_length=12)
    new_password: str = Field(min_length=8, max_length=128)


class PatientAuthTokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    account_type: str = "patient"


class PatientPasswordResetRequested(BaseModel):
    success: bool = True
    message: str
    channel: str
    destination_hint: str  # masked phone/email
