from uuid import UUID

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=150)
    password: str = Field(min_length=1, max_length=256)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class FacilityOption(BaseModel):
    facility_id: UUID
    facility_name: str


class FacilitySelectionRequest(BaseModel):
    facility_id: UUID
