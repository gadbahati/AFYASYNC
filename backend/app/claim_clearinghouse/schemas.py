from datetime import datetime
from decimal import Decimal
from uuid import UUID
from pydantic import BaseModel, Field

class RouteCreate(BaseModel):
    payer_id: UUID | None = None
    source_type: str = Field(min_length=2, max_length=40)
    adapter_code: str = Field(min_length=2, max_length=80)
    priority: int = Field(default=100, ge=1, le=10000)
    active: bool = True
    supports_submission: bool = False
    supports_callback: bool = False
    configuration: dict | None = None

class IntakeRequest(BaseModel):
    claim_id: UUID | None = None
    invoice_id: UUID | None = None
    idempotency_key: str = Field(min_length=8, max_length=180)

class StatusUpdate(BaseModel):
    status: str
    external_reference: str | None = None
    response_code: str | None = None
    response_message: str | None = None
    approved_amount: Decimal | None = None
    paid_amount: Decimal | None = None

class RemittanceRequest(BaseModel):
    external_reference: str | None = None
    status: str = "RECEIVED"
    approved_amount: Decimal = Field(default=Decimal("0"), ge=0)
    paid_amount: Decimal = Field(default=Decimal("0"), ge=0)
    patient_amount: Decimal = Field(default=Decimal("0"), ge=0)
    currency: str = Field(default="KES", min_length=3, max_length=3)
    metadata: dict | None = None

class CaseOut(BaseModel):
    id: UUID
    case_number: str
    claim_id: UUID | None
    invoice_id: UUID | None
    patient_id: UUID
    payer_id: UUID | None
    source_type: str
    adapter_code: str | None
    status: str
    claim_amount: Decimal
    approved_amount: Decimal
    paid_amount: Decimal
    external_reference: str | None
    denial_code: str | None
    denial_category: str | None
    denial_message: str | None
    attempt_count: int
    last_error: str | None
    queued_at: datetime | None
    submitted_at: datetime | None
    acknowledged_at: datetime | None
    resolved_at: datetime | None
    created_at: datetime
    model_config = {"from_attributes": True}
