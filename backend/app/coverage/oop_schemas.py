"""Multi-payer truth table and out-of-pocket estimate schemas."""

from datetime import date
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


class OopLineIn(BaseModel):
    service_code: str | None = Field(default=None, max_length=80)
    service_type: str | None = Field(default=None, max_length=60)
    description: str | None = Field(default=None, max_length=200)
    quantity: float = Field(default=1, gt=0, le=1000)
    unit_price: float = Field(gt=0, le=10_000_000)

    @model_validator(mode="after")
    def require_scope(self) -> "OopLineIn":
        if not (self.service_code and self.service_code.strip()) and not (
            self.service_type and self.service_type.strip()
        ):
            raise ValueError("SERVICE_SCOPE_REQUIRED")
        return self


class OopEstimateRequest(BaseModel):
    person_id: UUID
    lines: list[OopLineIn] = Field(min_length=1, max_length=50)
    # Optional preferred primary coverage; system still scores all verified covers
    preferred_coverage_id: UUID | None = None


class OopLineBreakdown(BaseModel):
    service_code: str | None
    service_type: str | None
    description: str | None
    line_total: float
    covered_amount: float
    patient_amount: float
    decision: str
    reason_code: str


class PayerOption(BaseModel):
    coverage_id: UUID
    payer_id: UUID
    payer_code: str
    payer_name: str
    payer_plan_id: UUID | None
    membership_number: str | None
    verification_status: str
    eligibility: str  # ELIGIBLE | UNVERIFIED | INACTIVE | EXPIRED | NOT_YET_ACTIVE
    gross_total: float
    covered_total: float
    patient_oop: float
    claimable: bool
    confidence: str  # HIGH | MEDIUM | LOW
    lines: list[OopLineBreakdown]
    notes: list[str] = Field(default_factory=list)


class StackedEstimate(BaseModel):
    """Primary + secondary coordination of benefits (simple residual model)."""

    primary_coverage_id: UUID
    secondary_coverage_id: UUID | None
    primary_payer_code: str
    secondary_payer_code: str | None
    gross_total: float
    primary_covered: float
    secondary_covered: float
    patient_oop: float
    note: str


class OopEstimateResponse(BaseModel):
    person_id: UUID
    facility_id: UUID | None
    effective_date: date
    gross_total: float
    cash_oop: float  # always full patient pay path
    options: list[PayerOption]
    recommended_coverage_id: UUID | None
    recommended_payer_code: str | None
    recommended_patient_oop: float
    stacked: StackedEstimate | None
    warnings: list[str] = Field(default_factory=list)
    guidance: str
