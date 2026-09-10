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


class FacilityResponse(FacilityCreate):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    facility_id: str
    status: str


class DepartmentCreate(BaseModel):
    name: str = Field(min_length=2, max_length=150)
    code: str = Field(min_length=2, max_length=50)


class DepartmentResponse(DepartmentCreate):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    facility_id: UUID
    status: str
