from uuid import UUID

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=150)
    password: str = Field(min_length=1, max_length=256)


class RefreshTokenRequest(BaseModel):
    refresh_token: str = Field(min_length=1)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class FacilityOption(BaseModel):
    facility_id: UUID
    facility_name: str


class FacilitySelectionRequest(BaseModel):
    facility_id: UUID


class FacilitySelectionRequired(BaseModel):
    """Returned by /login instead of TokenResponse when the user has active
    staff records at more than one facility.

    `access_token` here carries no facility_id, so it authenticates
    get_current_user (enough for /auth/me, /auth/facilities,
    /auth/select-facility, /auth/logout) but is rejected by
    get_facility_context / require_permission on every other endpoint until
    the client calls /select-facility to exchange it for a fully scoped
    TokenResponse (with a refresh token).
    """

    requires_facility_selection: bool = True
    access_token: str
    facilities: list[FacilityOption]
