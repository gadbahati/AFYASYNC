from pydantic import BaseModel, Field


class CareGapSignal(BaseModel):
    code: str
    severity: str  # LOW | MEDIUM | HIGH | CRITICAL
    title: str
    detail: str
    metric_value: float | int | None = None


class CountyCareGap(BaseModel):
    county: str
    facility_count: int = 0
    gap_score: int = Field(ge=0, le=100, description="0 healthy → 100 severe gaps")
    open_encounters: int = 0
    referral_out_30d: int = 0
    treat_abroad_open: int = 0
    appointment_requests_pending: int = 0
    claims_rejected_30d: int = 0
    claims_submitted_30d: int = 0
    rejection_rate_pct: float = 0.0
    low_stock_items: int = 0
    emergency_waiting: int = 0
    bed_occupancy_pct: float | None = None
    signals: list[CareGapSignal] = Field(default_factory=list)


class CareGapOverview(BaseModel):
    generated_at: str
    window_days: int
    national_gap_score: int = Field(ge=0, le=100)
    counties_scored: int = 0
    top_gap_counties: list[CountyCareGap] = Field(default_factory=list)
    national_signals: list[CareGapSignal] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)
