from uuid import UUID

from pydantic import BaseModel, ConfigDict


class NationalStaffResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    facility_id: UUID
    facility_code: str
    facility_name: str
    person_id: UUID
    employee_number: str
    professional_number: str | None
    department_id: UUID | None
    status: str


class NationalStaffListResponse(BaseModel):
    items: list[NationalStaffResponse]
    total: int
    limit: int
    offset: int
