from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class LabTestCreate(BaseModel):
    code: str = Field(min_length=2, max_length=50)
    name: str = Field(min_length=2, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    category: str | None = Field(default=None, max_length=100)
    sample_type: str | None = Field(default=None, max_length=100)
    price: float = Field(gt=0)


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
    forwarded_at: datetime | None = None
    forwarded_by: UUID | None = None
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


class LabOrderItemResponse(BaseModel):
    id: UUID
    test_id: UUID
    test_code: str
    test_name: str
    description: str | None
    category: str | None
    sample_type: str | None
    price: float
    instructions: str | None
    status: str
    charge_id: UUID | None
    result: ResultResponse | None


class LabOrderDetailResponse(BaseModel):
    id: UUID
    order_id: str
    encounter_id: UUID
    patient_id: UUID
    priority: str
    status: str
    forwarded_at: datetime | None
    items: list[LabOrderItemResponse]
    total_amount: float


class LabForwardResponse(BaseModel):
    order_id: str
    status: str
    forwarded_at: datetime
    message: str
