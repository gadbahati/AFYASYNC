from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class FacilityCreate(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    facility_type: str = Field(min_length=2, max_length=50)
    registration_number: str | None = None
    license_number: str | None = None
    county: str | None = None
    sub_county: str | None = None
    address: str | None = None
    phone: str | None = None
    email: str | None = None


class FacilityQuickCreate(BaseModel):
    """Minimal payload for adding a facility on the fly from the onboarding
    'Select facility' search screen, when it isn't already in the directory."""

    name: str = Field(min_length=2, max_length=200)
    facility_type: str = Field(default="HOSPITAL", min_length=2, max_length=50)
    county: str | None = None
    sub_county: str | None = None


class FacilityUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=200)
    facility_type: str | None = Field(default=None, min_length=2, max_length=50)
    registration_number: str | None = None
    license_number: str | None = None
    county: str | None = None
    sub_county: str | None = None
    address: str | None = None
    phone: str | None = None
    email: str | None = None


class FacilityStatusUpdate(BaseModel):
    status: Literal["APPLICATION", "ACTIVE", "SUSPENDED", "INACTIVE"]
    reason: str = Field(min_length=3, max_length=500)


class FacilityResponse(FacilityCreate):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    facility_id: str
    status: str


class NetworkFacilityResponse(FacilityResponse):
    """Facility record exposed to explicitly privileged national operators."""

    created_at: datetime
    updated_at: datetime


class DepartmentCreate(BaseModel):
    name: str = Field(min_length=2, max_length=150)
    code: str = Field(min_length=2, max_length=50)


class DepartmentStatusUpdate(BaseModel):
    status: Literal["ACTIVE", "INACTIVE"]


class DepartmentResponse(DepartmentCreate):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    facility_id: UUID
    status: str
