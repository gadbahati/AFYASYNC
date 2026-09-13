from datetime import date
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


BenefitRuleStatus = Literal["ACTIVE", "INACTIVE"]


class BenefitRuleAdminCreate(BaseModel):
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
    def validate_rule(self):
        if not self.service_code and not self.service_type:
            raise ValueError("BENEFIT_SCOPE_REQUIRED")
        if self.effective_from and self.effective_to and self.effective_to < self.effective_from:
            raise ValueError("INVALID_BENEFIT_DATES")
        return self


class BenefitRuleAdminUpdate(BaseModel):
    service_code: str | None = Field(default=None, max_length=80)
    service_type: str | None = Field(default=None, max_length=60)
    payer_percent: float | None = Field(default=None, ge=0, le=100)
    fixed_patient_copay: float | None = Field(default=None, ge=0)
    max_covered_amount: float | None = Field(default=None, ge=0)
    effective_from: date | None = None
    effective_to: date | None = None


class BenefitRuleStatusUpdate(BaseModel):
    status: BenefitRuleStatus
    reason: str = Field(min_length=3, max_length=500)


class BenefitRuleAdminResponse(BenefitRuleAdminCreate):
    id: UUID
    status: str
    model_config = {"from_attributes": True}
