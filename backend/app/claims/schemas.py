from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


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
    errors: list[str] = Field(default_factory=list, max_length=50)


class ClaimSubmitOut(BaseModel):
    claim_id: UUID
    status: str
    message: str


class PayerResponseCreate(BaseModel):
    status: str = Field(min_length=3, max_length=40)
    response_code: str | None = Field(default=None, max_length=80)
    response_message: str | None = Field(default=None, max_length=500)
    external_reference: str | None = Field(default=None, max_length=150)
    approved_amount: Decimal | None = Field(default=None, ge=0, le=Decimal("100000000"))

    @field_validator("status")
    @classmethod
    def normalize_status(cls, value: str) -> str:
        return value.strip().upper()

    @field_validator("response_code", "response_message", "external_reference")
    @classmethod
    def strip_optional(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None


class ReconcileCreate(BaseModel):
    received_amount: Decimal = Field(ge=0, le=Decimal("100000000"))


class ReconcileResponse(BaseModel):
    claim_id: UUID
    expected_amount: Decimal
    received_amount: Decimal
    difference: Decimal
    status: str
