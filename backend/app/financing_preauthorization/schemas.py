from uuid import UUID
from pydantic import BaseModel, Field

class FinancingPreauthRequest(BaseModel):
    person_id: UUID
    coverage_id: UUID
    payer_id: UUID
    service_code: str | None = Field(default=None, max_length=80)
    service_type: str | None = Field(default=None, max_length=60)
    requested_amount: float = Field(ge=0)

class FinancingPreauthDecision(BaseModel):
    status: str = Field(pattern="^(AUTHORIZED|REJECTED|CONDITIONAL)$")
    approved_amount: float = Field(ge=0)
    external_reference: str | None = Field(default=None, max_length=150)

class FinancingPreauthResponse(BaseModel):
    id: UUID
    authorization_number: str
    person_id: UUID
    facility_id: UUID
    coverage_id: UUID
    payer_id: UUID
    service_code: str | None
    service_type: str | None
    requested_amount: float
    approved_amount: float
    status: str
    decision_reason: str | None
    external_reference: str | None
    evidence: dict | None
    model_config = {"from_attributes": True}
