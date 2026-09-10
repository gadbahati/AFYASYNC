from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field


class ClaimCreate(BaseModel):
    invoice_id: UUID


class ClaimResponseOut(BaseModel):
    id: UUID
    claim_id: str
    invoice_id: UUID
    payer_id: UUID
    claim_amount: Decimal
    approved_amount: Decimal
    paid_amount: Decimal
    status: str

    model_config = {"from_attributes": True}


class ClaimValidationOut(BaseModel):
    claim_id: UUID
    valid: bool
    errors: list[str] = Field(default_factory=list)


class ClaimSubmitOut(BaseModel):
    claim_id: UUID
    status: str
    message: str


class PayerResponseCreate(BaseModel):
    status: str
    response_code: str | None = None
    response_message: str | None = None
    external_reference: str | None = None
    approved_amount: Decimal | None = Field(default=None, ge=0)


class ReconcileCreate(BaseModel):
    received_amount: Decimal = Field(ge=0)


class ReconcileResponse(BaseModel):
    claim_id: UUID
    expected_amount: Decimal
    received_amount: Decimal
    difference: Decimal
    status: str
