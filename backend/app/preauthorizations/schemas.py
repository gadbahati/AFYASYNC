from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class PreAuthorizationCreate(BaseModel):
    patient_id: UUID
    coverage_id: UUID
    payer_id: UUID
    benefit_package_code: str = Field(min_length=2, max_length=80)
    care_setting: str = Field(pattern="^(OUTPATIENT|INPATIENT)$")
    department: str = Field(min_length=2, max_length=50)
    requested_services: list[str] = Field(min_length=1, max_length=100)
    requested_amount: float = Field(ge=0)
    encounter_id: UUID | None = None


class PreAuthorizationDecision(BaseModel):
    status: str = Field(pattern="^(AUTHORIZED|REJECTED|AUTHORIZED_PENDING_VISIT)$")
    approved_amount: float = Field(ge=0)
    external_reference: str | None = Field(default=None, max_length=150)


class PreAuthorizationResponse(BaseModel):
    id: UUID
    authorization_number: str
    patient_id: UUID
    benefit_package_code: str
    care_setting: str
    department: str
    requested_services: list[str]
    status: str
    requested_amount: float
    approved_amount: float
    external_reference: str | None
    requested_at: datetime
    decided_at: datetime | None

    model_config = {"from_attributes": True}
