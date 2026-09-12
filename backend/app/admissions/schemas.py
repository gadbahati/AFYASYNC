from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class SHAMemberLookupResponse(BaseModel):
    person_id: UUID
    afya_id: str
    membership_number: str
    full_name: str
    date_of_birth: str | None
    sex: str | None
    coverage_status: str
    coverage_id: UUID
    payer_id: UUID
    benefit_package_codes: list[str]


class AdmissionCreate(BaseModel):
    patient_id: UUID
    department_id: UUID
    benefit_package_code: str = Field(min_length=1, max_length=80)
    ward: str = Field(min_length=1, max_length=120)
    bed: str = Field(min_length=1, max_length=50)
    diagnosis: str | None = Field(default=None, max_length=2000)


class AdmissionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    admission_number: str
    patient_id: UUID
    facility_id: UUID
    encounter_id: UUID
    benefit_package_code: str
    ward: str
    bed: str
    diagnosis: str | None
    status: str
    admitted_at: datetime
    discharged_at: datetime | None
