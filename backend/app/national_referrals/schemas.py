from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class NationalReferralItem(BaseModel):
    id: UUID
    referral_id: str
    source_facility_id: UUID
    source_facility_code: str
    source_facility_name: str
    source_county: str | None
    destination_facility_id: UUID
    destination_facility_code: str
    destination_facility_name: str
    destination_county: str | None
    destination_department_id: UUID | None
    destination_department_name: str | None
    priority: str
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class NationalReferralStatusCount(BaseModel):
    status: str
    count: int = Field(ge=0)


class NationalReferralPriorityCount(BaseModel):
    priority: str
    count: int = Field(ge=0)


class NationalReferralResponse(BaseModel):
    items: list[NationalReferralItem]
    total: int = Field(ge=0)
    limit: int = Field(ge=1, le=200)
    offset: int = Field(ge=0, le=10000)
    status_counts: list[NationalReferralStatusCount]
    priority_counts: list[NationalReferralPriorityCount]
