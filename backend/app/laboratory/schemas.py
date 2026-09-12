from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class LabTestCreate(BaseModel):
    code: str = Field(min_length=2, max_length=50)
    name: str = Field(min_length=2, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    category: str | None = None
    sample_type: str | None = None
    price: float = Field(default=0, ge=0)


class LabTestResponse(LabTestCreate):
    id: UUID
    status: str


class LabOrderItemCreate(BaseModel):
    test_id: UUID
    instructions: str | None = None


class LabOrderCreate(BaseModel):
    encounter_id: UUID
    priority: str = Field(default="NORMAL", pattern="^(NORMAL|URGENT|EMERGENCY)$")
    items: list[LabOrderItemCreate] = Field(min_length=1)


class LabOrderResponse(BaseModel):
    id: UUID
    order_id: str
    encounter_id: UUID
    patient_id: UUID
    ordered_by: UUID
    priority: str
    status: str
    created_at: datetime


class SampleCollect(BaseModel):
    lab_order_item_id: UUID


class SampleResponse(BaseModel):
    id: UUID
    sample_id: str
    lab_order_item_id: UUID
    collected_by: UUID
    collected_at: datetime
    received_at: datetime | None
    status: str


class SampleReceive(BaseModel):
    sample_id: UUID


class ResultCreate(BaseModel):
    lab_order_item_id: UUID
    sample_id: UUID
    result: str = Field(min_length=1)
    unit: str | None = None
    reference_range: str | None = None
    comments: str | None = None


class ResultResponse(ResultCreate):
    id: UUID
    entered_by: UUID
    verified_by: UUID | None
    status: str
    created_at: datetime
    verified_at: datetime | None
