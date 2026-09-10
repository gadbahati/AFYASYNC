from datetime import date
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


class CoverageCreate(BaseModel):
    person_id: UUID
    payer_id: UUID
    payer_plan_id: UUID | None = None
    membership_number: str | None = Field(default=None, max_length=100)
    start_date: date | None = None
    end_date: date | None = None


class CoverageResponse(BaseModel):
    id: UUID
    person_id: UUID
    payer_id: UUID
    payer_plan_id: UUID | None
    membership_number: str | None
    start_date: date | None
    end_date: date | None
    verification_status: str
    status: str


class BenefitRuleCreate(BaseModel):
    payer_id: UUID
    payer_plan_id: UUID | None = None
    service_code: str | None = Field(default=None, max_length=80)
    service_type: str | None = Field(default=None, max_length=60)
    payer_percent: float = Field(default=100, ge=0, le=100)
    fixed_patient_copay: float = Field(default=0, ge=0)
    max_covered_amount: float | None = Field(default=None, ge=0)
    effective_from: date | None = None
    effective_to: date | None = None

    @model_validator(mode="after")
    def validate_scope_and_dates(self):
        if not self.service_code and not self.service_type:
            raise ValueError("BENEFIT_SCOPE_REQUIRED")
        if self.effective_from and self.effective_to and self.effective_to < self.effective_from:
            raise ValueError("INVALID_BENEFIT_DATES")
        return self


class BenefitRuleResponse(BenefitRuleCreate):
    id: UUID
    status: str

    model_config = {"from_attributes": True}
