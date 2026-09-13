from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


PayerStatus = Literal["APPLICATION", "ACTIVE", "SUSPENDED", "INACTIVE"]
PlanStatus = Literal["ACTIVE", "INACTIVE"]


class PayerCreate(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    payer_type: str = Field(min_length=2, max_length=50)
    code: str = Field(min_length=2, max_length=50)


class PayerUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=200)
    payer_type: str | None = Field(default=None, min_length=2, max_length=50)


class PayerStatusUpdate(BaseModel):
    status: PayerStatus
    reason: str = Field(min_length=3, max_length=500)


class PayerAdminResponse(BaseModel):
    id: UUID
    name: str
    payer_type: str
    code: str
    status: str
    integration_status: str

    model_config = {"from_attributes": True}


class PayerPlanCreate(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    code: str = Field(min_length=2, max_length=50)


class PayerPlanUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=200)


class PayerPlanStatusUpdate(BaseModel):
    status: PlanStatus


class PayerPlanAdminResponse(BaseModel):
    id: UUID
    payer_id: UUID
    name: str
    code: str
    status: str

    model_config = {"from_attributes": True}
