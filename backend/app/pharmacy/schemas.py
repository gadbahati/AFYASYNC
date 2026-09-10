from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, Field


class MedicationCreate(BaseModel):
    code: str = Field(min_length=1, max_length=50)
    name: str = Field(min_length=1, max_length=200)
    generic_name: str | None = None
    strength: str | None = None
    form: str | None = None
    unit: str | None = None


class MedicationResponse(MedicationCreate):
    id: UUID
    status: str


class PrescriptionItemCreate(BaseModel):
    medication_id: UUID
    dose: str = Field(min_length=1, max_length=100)
    frequency: str = Field(min_length=1, max_length=100)
    duration: str = Field(min_length=1, max_length=100)
    route: str | None = None
    quantity: float = Field(gt=0)
    instructions: str | None = None


class PrescriptionCreate(BaseModel):
    encounter_id: UUID
    items: list[PrescriptionItemCreate] = Field(min_length=1)


class PrescriptionResponse(BaseModel):
    id: UUID
    prescription_id: str
    encounter_id: UUID
    patient_id: UUID
    prescribed_by: UUID
    status: str
    created_at: datetime


class InventoryReceive(BaseModel):
    facility_id: UUID
    medication_id: UUID
    batch_number: str = Field(min_length=1, max_length=100)
    expiry_date: date
    quantity: float = Field(gt=0)
    purchase_price: float = Field(ge=0)
    selling_price: float = Field(ge=0)


class InventoryResponse(BaseModel):
    id: UUID
    facility_id: UUID
    medication_id: UUID
    current_quantity: float
    minimum_quantity: float
    status: str


class DispenseBillingItem(BaseModel):
    prescription_item_id: UUID
    service_id: UUID


class DispenseRequest(BaseModel):
    billing_items: list[DispenseBillingItem] = Field(min_length=1)


class DispenseResponse(BaseModel):
    prescription_id: UUID
    status: str
    movements_created: int
    charges_created: int
