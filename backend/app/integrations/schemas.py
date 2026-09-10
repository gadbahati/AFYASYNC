from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field


class IntegrationCreate(BaseModel):
    name: str = Field(min_length=2, max_length=150)
    integration_type: str = Field(min_length=2, max_length=60)
    provider: str = Field(min_length=2, max_length=120)
    configuration: dict = Field(default_factory=dict)


class IntegrationOut(BaseModel):
    id: UUID
    facility_id: UUID
    name: str
    integration_type: str
    provider: str
    status: str

    model_config = {"from_attributes": True}


class TransactionCreate(BaseModel):
    transaction_id: str = Field(min_length=1, max_length=120)
    entity_type: str = Field(min_length=1, max_length=80)
    entity_id: UUID | None = None
    direction: str = Field(pattern="^(OUTBOUND|INBOUND)$")
    request_reference: str | None = Field(default=None, max_length=150)


class TransactionOut(BaseModel):
    id: UUID
    integration_id: UUID
    transaction_id: str
    status: str
    attempt_count: int
    external_reference: str | None
    response_code: str | None
    response_data: dict

    model_config = {"from_attributes": True}


class PayerCallbackCreate(BaseModel):
    status: str = Field(min_length=2, max_length=30)
    response_code: str | None = Field(default=None, max_length=80)
    response_message: str | None = Field(default=None, max_length=500)
    external_reference: str = Field(min_length=1, max_length=150)
    approved_amount: Decimal | None = Field(default=None, ge=0)


class PaymentCallbackCreate(BaseModel):
    status: str = Field(min_length=2, max_length=30)
    response_code: str | None = Field(default=None, max_length=80)
    response_message: str | None = Field(default=None, max_length=500)
    external_reference: str = Field(min_length=1, max_length=150)
