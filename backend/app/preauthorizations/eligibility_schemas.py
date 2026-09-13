from datetime import date
from uuid import UUID

from pydantic import BaseModel, Field


class EligibilityCheckRequest(BaseModel):
    patient_id: UUID
    coverage_id: UUID
    service_code: str | None = Field(default=None, max_length=80)
    service_type: str | None = Field(default=None, max_length=60)
    as_of: date | None = None


class EligibilityCheckResponse(BaseModel):
    eligible: bool
    reason: str
    coverage_id: UUID
    payer_id: UUID | None = None
    payer_plan_id: UUID | None = None
    benefit_rule_id: UUID | None = None
    payer_percent: float | None = None
    fixed_patient_copay: float | None = None
    max_covered_amount: float | None = None
