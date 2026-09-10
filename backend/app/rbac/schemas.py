from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class RoleCreate(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    description: str | None = None


class PermissionCreate(BaseModel):
    code: str = Field(min_length=2, max_length=120)
    description: str | None = None


class StaffCreate(BaseModel):
    facility_id: UUID
    person_id: UUID
    employee_number: str = Field(min_length=1, max_length=100)
    professional_number: str | None = None
    department_id: UUID | None = None


class StaffResponse(StaffCreate):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    status: str


class RoleResponse(RoleCreate):
    model_config = ConfigDict(from_attributes=True)

    id: UUID


class PermissionResponse(PermissionCreate):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
