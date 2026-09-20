from uuid import UUID

from pydantic import BaseModel, Field


class RiskFactorOut(BaseModel):
    code: str
    severity: str
    points: int = Field(ge=0, le=100)
    message: str
    owner: str


class ClaimPreflightResponse(BaseModel):
    invoice_id: UUID
    ready: bool
    errors: list[str] = Field(default_factory=list, max_length=50)
    warnings: list[str] = Field(default_factory=list, max_length=50)
    payer_id: UUID | None = None
    coverage_id: UUID | None = None
    payer_amount: float = Field(default=0, ge=0, le=100_000_000)
    patient_amount: float = Field(default=0, ge=0, le=100_000_000)
    item_count: int = Field(default=0, ge=0, le=10_000)
    # Phase 11 — rejection prevention
    risk_score: int = Field(default=0, ge=0, le=100)
    risk_band: str = Field(default="LOW")
    block_submit: bool = False
    risk_factors: list[RiskFactorOut] = Field(default_factory=list)


class FacilityKesAtRiskResponse(BaseModel):
    facility_id: str
    window_days: int
    kes_at_risk: float
    kes_rejected: float
    kes_in_flight: float
    kes_draft_or_ready: float
    count_rejected: int
    count_in_flight: int
    count_draft_or_ready: int
    as_of: str
