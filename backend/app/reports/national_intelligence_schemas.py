from typing import Literal
from uuid import UUID

from pydantic import BaseModel


IntelligenceSeverity = Literal["CRITICAL", "HIGH", "MEDIUM", "LOW"]
IntelligenceCategory = Literal["FINANCING", "CLINICAL_OPERATIONS", "SUPPLY", "INTEGRATIONS"]


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


class NationalIntelligenceResponse(BaseModel):
    start_date: str
    end_date: str
    generated_at: str
    alerts: list[NationalIntelligenceAlert]
    facility_signals: list[NationalFacilitySignal]
