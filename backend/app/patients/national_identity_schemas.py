from datetime import date
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class NationalIdentityResolution(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    afya_id: str = Field(min_length=1, max_length=20)
    person_id: UUID
    first_name: str = Field(min_length=1, max_length=100)
    middle_name: str | None = Field(default=None, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    date_of_birth: date | None = None
    sex: str | None = Field(default=None, max_length=30)
    patient_status: str = Field(min_length=1, max_length=30)
    active_facility_count: int = Field(ge=0)
    identity_status: str = Field(min_length=1, max_length=30)
