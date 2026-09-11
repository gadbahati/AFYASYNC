from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class ReferralCreate(BaseModel):
    encounter_id: UUID
    destination_facility_id: UUID
    destination_department_id: UUID | None = None
    reason: str = Field(min_length=3, max_length=4000)
    priority: str = Field(default="ROUTINE", pattern="^(ROUTINE|URGENT|EMERGENCY)$")
    clinical_summary: str | None = Field(default=None, max_length=10000)


class ReferralStatusUpdate(BaseModel):
    status: str = Field(pattern="^(SENT|ACCEPTED|IN_PROGRESS|COMPLETED|DECLINED|CANCELLED)$")


class TransferCreate(BaseModel):
    encounter_id: UUID
    destination_facility_id: UUID
    referral_id: UUID | None = None
    reason: str = Field(min_length=3, max_length=4000)
    notes: str | None = Field(default=None, max_length=5000)


class TransferStatusUpdate(BaseModel):
    status: str = Field(pattern="^(ACCEPTED|IN_TRANSIT|ARRIVED|CANCELLED)$")


class ReferralOut(BaseModel):
    id: UUID
    referral_id: str
    patient_id: UUID
    encounter_id: UUID
    source_facility_id: UUID
    destination_facility_id: UUID
    destination_department_id: UUID | None
    referred_by: UUID
    reason: str
    priority: str
    clinical_summary: str | None
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TransferOut(BaseModel):
    id: UUID
    transfer_id: str
    referral_id: UUID | None
    patient_id: UUID
    encounter_id: UUID
    source_facility_id: UUID
    destination_facility_id: UUID
    requested_by: UUID
    reason: str
    status: str
    notes: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ReferralListResponse(BaseModel):
    items: list[ReferralOut]
    total: int
    limit: int
    offset: int


class TransferListResponse(BaseModel):
    items: list[TransferOut]
    total: int
    limit: int
    offset: int
