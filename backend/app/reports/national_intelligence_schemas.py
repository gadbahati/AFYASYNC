from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

IntelligenceSeverity = Literal["CRITICAL", "HIGH", "MEDIUM", "LOW"]
IntelligenceCategory = Literal["FINANCING", "CLINICAL_OPERATIONS", "SUPPLY", "INTEGRATIONS"]
TrendDirection = Literal["UP", "DOWN", "FLAT"]


class NationalIntelligenceAlert(BaseModel):
    code: str = Field(min_length=1, max_length=100)
    severity: IntelligenceSeverity
    category: IntelligenceCategory
    title: str = Field(min_length=1, max_length=200)
    summary: str = Field(min_length=1, max_length=1000)
    value: float = Field(ge=0)
    unit: str = Field(min_length=1, max_length=50)
    recommendation: str = Field(min_length=1, max_length=1000)


class NationalFacilitySignal(BaseModel):
    facility_id: UUID
    facility_code: str = Field(min_length=1, max_length=100)
    facility_name: str = Field(min_length=1, max_length=200)
    county: str | None = Field(default=None, max_length=100)
    score: int = Field(ge=0, le=100)
    severity: IntelligenceSeverity
    signals: list[str] = Field(default_factory=list, max_length=20)


class NationalIntelligenceTrend(BaseModel):
    metric: str = Field(min_length=1, max_length=100)
    label: str = Field(min_length=1, max_length=200)
    current: float = Field(ge=0)
    previous: float = Field(ge=0)
    change_percent: float | None = Field(default=None)
    direction: TrendDirection
    interpretation: str = Field(min_length=1, max_length=500)


class NationalCountyIntelligence(BaseModel):
    county: str = Field(min_length=1, max_length=100)
    facilities: int = Field(ge=0)
    facilities_requiring_review: int = Field(ge=0)
    encounters: int = Field(ge=0)
    billed: float = Field(ge=0)
    confirmed_payments: float = Field(ge=0)
    claims_receivable: float = Field(ge=0)
    average_review_score: float = Field(ge=0, le=100)
    highest_review_score: int = Field(ge=0, le=100)


class NationalIntelligenceResponse(BaseModel):
    start_date: str
    end_date: str
    comparison_start_date: str
    comparison_end_date: str
    generated_at: str
    alerts: list[NationalIntelligenceAlert] = Field(default_factory=list)
    facility_signals: list[NationalFacilitySignal] = Field(default_factory=list)
    facility_signals_total: int = Field(default=0, ge=0)
    facility_signals_page: int = Field(default=1, ge=1)
    facility_signals_page_size: int = Field(default=100, ge=1, le=500)
    trends: list[NationalIntelligenceTrend] = Field(default_factory=list)
    counties: list[NationalCountyIntelligence] = Field(default_factory=list)
