from datetime import date
from uuid import UUID

from pydantic import BaseModel, Field


class ServiceCreate(BaseModel):
    code: str = Field(min_length=1, max_length=80)
    name: str = Field(min_length=1, max_length=200)
    department_id: UUID | None = None
    service_type: str = Field(min_length=1, max_length=60)
    price: float = Field(gt=0)


class ServiceResponse(ServiceCreate):
    id: UUID
    facility_id: UUID
    status: str

    model_config = {"from_attributes": True}


class ChargeCreate(BaseModel):
    encounter_id: UUID
    service_id: UUID
    quantity: float = Field(gt=0)
    source_type: str = Field(min_length=1, max_length=50)
    source_id: UUID | None = None


class ChargeResponse(BaseModel):
    id: UUID
    charge_id: str
    encounter_id: UUID
    patient_id: UUID
    facility_id: UUID
    service_id: UUID
    quantity: float
    unit_price: float
    total_amount: float
    source_type: str
    source_id: UUID | None
    status: str

    model_config = {"from_attributes": True}


class InvoiceResponse(BaseModel):
    id: UUID
    invoice_id: str
    patient_id: UUID
    facility_id: UUID
    encounter_id: UUID
    subtotal: float
    payer_amount: float
    patient_amount: float
    total_amount: float
    status: str

    model_config = {"from_attributes": True}


class PaymentCreate(BaseModel):
    invoice_id: UUID
    amount: float = Field(gt=0)
    payment_method: str = Field(min_length=1, max_length=40)
    provider: str | None = Field(default=None, max_length=80)
    external_reference: str | None = Field(default=None, max_length=150)


class PaymentResponse(BaseModel):
    id: UUID
    transaction_id: str
    invoice_id: UUID
    patient_id: UUID
    facility_id: UUID
    amount: float
    payment_method: str
    provider: str | None
    external_reference: str | None
    status: str

    model_config = {"from_attributes": True}
