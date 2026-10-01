from uuid import UUID
from pydantic import BaseModel, Field

class AnomalyCaseUpdate(BaseModel):
    status: str = Field(min_length=2, max_length=30)
    note: str | None = Field(default=None, max_length=2000)

class AnomalyCaseOut(BaseModel):
    id: UUID
    case_number: str
    facility_id: UUID
    anomaly_type: str
    severity: str
    risk_score: int
    status: str
    claim_id: UUID | None
    invoice_id: UUID | None
    patient_id: UUID | None
    payer_id: UUID | None
    recovery_case_id: UUID | None
    amount_at_risk: float
    summary: str
    evidence: dict | None
    notes: str | None
    created_at: object
    resolved_at: object | None
    class Config:
        from_attributes = True
