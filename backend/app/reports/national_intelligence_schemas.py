from typing import Literal
from uuid import UUID
from pydantic import BaseModel

IntelligenceSeverity = Literal["CRITICAL", "HIGH", "MEDIUM", "LOW"]
IntelligenceCategory = Literal["FINANCING", "CLINICAL_OPERATIONS", "SUPPLY", "INTEGRATIONS"]
TrendDirection = Literal["UP", "DOWN", "FLAT"]

class NationalIntelligenceAlert(BaseModel):
    code: str
    severity: IntelligenceSeverity
    category: IntelligenceCategory
    title: str
    summary: str
    value: int | float
    unit: str
    recommendation: str

class NationalFacilitySignal(BaseModel):
    facility_id: UUID
    facility_code: str
    facility_name: str
    county: str | None
    score: int
    severity: IntelligenceSeverity
    signals: list[str]

class NationalIntelligenceTrend(BaseModel):
    metric: str
    label: str
    current: float
    previous: float
    change_percent: float | None
    direction: TrendDirection
    interpretation: str

class NationalCountyIntelligence(BaseModel):
    county: str
    facilities: int
    facilities_requiring_review: int
    encounters: int
    billed: float
    confirmed_payments: float
    claims_receivable: float
    average_review_score: float
    highest_review_score: int

class NationalIntelligenceResponse(BaseModel):
    start_date: str
    end_date: str
    comparison_start_date: str
    comparison_end_date: str
    generated_at: str
    alerts: list[NationalIntelligenceAlert]
    facility_signals: list[NationalFacilitySignal]
    trends: list[NationalIntelligenceTrend]
    counties: list[NationalCountyIntelligence]
