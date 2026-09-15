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
    expires_in: int


class FacilityOption(BaseModel):
    facility_id: UUID
    facility_name: str
    county: str | None = None
    sub_county: str | None = None
    facility_type: str | None = None
    registration_number: str | None = None


class FacilitySelectionRequest(BaseModel):
    facility_id: UUID


class FacilitySelectionRequired(BaseModel):
    """Returned by /login while the user chooses an active facility."""

    requires_facility_selection: bool = True
    access_token: str
    facilities: list[FacilityOption]
