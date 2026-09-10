from datetime import date
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class PatientCreate(BaseModel):
    first_name: str = Field(min_length=1, max_length=100)
    middle_name: str | None = Field(default=None, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    date_of_birth: date | None = None
    sex: str | None = Field(default=None, max_length=30)
    phone: str | None = Field(default=None, max_length=30)
    email: str | None = Field(default=None, max_length=320)
    address: str | None = Field(default=None, max_length=500)
    emergency_contact_name: str | None = Field(default=None, max_length=200)
    emergency_contact_phone: str | None = Field(default=None, max_length=30)
    next_of_kin_name: str | None = Field(default=None, max_length=200)
    next_of_kin_phone: str | None = Field(default=None, max_length=30)


class PatientResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    afya_id: str
    first_name: str
    middle_name: str | None
    last_name: str
    date_of_birth: date | None
    sex: str | None
    phone: str | None
    email: str | None
    status: str


class PatientSearchResult(BaseModel):
    id: UUID
    afya_id: str
    full_name: str
    phone: str | None
    status: str
