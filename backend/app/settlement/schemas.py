from datetime import datetime
from decimal import Decimal
from uuid import UUID
from pydantic import BaseModel, Field

class ObligationRequest(BaseModel):
    claim_id: UUID

class BatchCreateRequest(BaseModel):
    payer_id: UUID

class PaymentRequest(BaseModel):
    obligation_id: UUID
    amount: Decimal = Field(ge=0)
    method: str = Field(min_length=2, max_length=40)
    external_reference: str | None = Field(default=None, max_length=150)

class ReconcileRequest(BaseModel):
    received_amount: Decimal = Field(ge=0)

class SettlementResponse(BaseModel):
    id: UUID
    status: str
    amount: Decimal
    reference: str | None = None
    created_at: datetime | None = None
    model_config = {"from_attributes": True}
