from decimal import Decimal
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, Field

class AdjudicationResponse(BaseModel):
    id: UUID
    claim_id: UUID
    decision: str
    submitted_amount: Decimal
    allowed_amount: Decimal
    patient_amount: Decimal
    reason_code: str
    evidence: dict | None
    adjudicated_at: datetime
    model_config = {"from_attributes": True}

class AdjudicationRunRequest(BaseModel):
    claim_id: UUID
    force: bool = False
