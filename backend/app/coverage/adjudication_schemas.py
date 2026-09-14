from datetime import date
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


class BenefitAdjudicationRequest(BaseModel):
    coverage_id: UUID
    service_code: str | None = Field(default=None, min_length=1, max_length=80)
    service_type: str | None = Field(default=None, min_length=1, max_length=60)
    requested_amount: float = Field(gt=0, le=10_000_000)

    @model_validator(mode="after")
    def require_service_scope(self) -> "BenefitAdjudicationRequest":
        if not self.service_code and not self.service_type:
            raise ValueError("SERVICE_SCOPE_REQUIRED")
        return self


class BenefitAdjudicationResponse(BaseModel):
    coverage_id: UUID
    person_id: UUID
    payer_id: UUID
    payer_plan_id: UUID | None
    service_code: str | None
    service_type: str | None
    requested_amount: float
    covered_amount: float
    patient_amount: float
    payer_percent: float
    fixed_patient_copay: float
    max_covered_amount: float | None
    decision: str
    reason_code: str
    effective_date: date
