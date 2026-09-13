from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field


class SimulatedLine(BaseModel):
    code: str = Field(min_length=1, max_length=80)
    description: str = Field(min_length=1, max_length=200)
    quantity: float = Field(gt=0, default=1)
    unit_price: Decimal = Field(ge=0)


class CoverageSimulateRequest(BaseModel):
    coverage_mode: str = Field(pattern="^(AFYASYNC|SHA|CASH|OTHER)$")
    patient_id: UUID | None = None
    membership_number: str | None = Field(default=None, max_length=80)
    lines: list[SimulatedLine] = Field(min_length=1)


class SimulatedLineResult(BaseModel):
    code: str
    description: str
    quantity: float
    unit_price: Decimal
    line_total: Decimal
    payer_share: Decimal
    patient_share: Decimal
    note: str


class CoverageSimulateResponse(BaseModel):
    coverage_mode: str
    eligibility: str
    eligibility_detail: str
    gross_total: Decimal
    payer_total: Decimal
    patient_total: Decimal
    claimable: bool
    warnings: list[str]
    lines: list[SimulatedLineResult]
    guidance: str


class CommandCentreMetric(BaseModel):
    key: str
    label: str
    value: int | float | str
    unit: str | None = None
    tone: str = "neutral"  # neutral | good | warn | bad


class CommandCentreResponse(BaseModel):
    facility_id: UUID
    generated_at: str
    metrics: list[CommandCentreMetric]
    claim_pipeline: dict[str, int]
    coverage_mix: dict[str, int]
    alerts: list[str]


class FraudSignal(BaseModel):
    code: str
    severity: str  # LOW | MEDIUM | HIGH
    title: str
    detail: str
    resource_type: str | None = None
    resource_id: str | None = None


class FraudRadarResponse(BaseModel):
    facility_id: UUID
    scanned_at: str
    signals: list[FraudSignal]
    summary: str
