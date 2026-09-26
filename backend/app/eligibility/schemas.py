from datetime import date
from uuid import UUID
from pydantic import BaseModel, Field
class EligibilityRequest(BaseModel):
    person_id: UUID
    service_code: str | None = None
    service_type: str | None = None
    payer_id: UUID | None = None
    payer_plan_id: UUID | None = None
    gross_amount: float = Field(default=0, ge=0)
class EligibilityResponse(BaseModel):
    decision: str
    reason_code: str
    person_id: UUID
    payer_id: UUID | None = None
    payer_plan_id: UUID | None = None
    coverage_id: UUID | None = None
    estimated_payer_amount: float
    estimated_patient_amount: float
    evaluated_at: str
    evidence: dict = {}
