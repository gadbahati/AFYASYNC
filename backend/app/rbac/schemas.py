from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class RoleCreate(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    description: str | None = None


class PermissionCreate(BaseModel):
    code: str = Field(min_length=2, max_length=120)
    description: str | None = None


class StaffCreate(BaseModel):
    person_id: UUID
    employee_number: str = Field(min_length=1, max_length=100)
    professional_number: str | None = None
    department_id: UUID | None = None


class StaffStatusUpdate(BaseModel):
    status: Literal["ACTIVE", "INACTIVE"]


class StaffRoleAssign(BaseModel):
    role_id: UUID


class StaffResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    facility_id: UUID
    person_id: UUID
    employee_number: str
    professional_number: str | None
    department_id: UUID | None
    status: str


class StaffListResponse(BaseModel):
    items: list[StaffResponse]
    total: int
    limit: int
    offset: int


class StaffRoleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    staff_id: UUID
    role_id: UUID
    facility_id: UUID


class RoleResponse(RoleCreate):
    model_config = ConfigDict(from_attributes=True)

    id: UUID


class PermissionResponse(PermissionCreate):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
