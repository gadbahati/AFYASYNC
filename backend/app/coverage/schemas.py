from datetime import date
from uuid import UUID

from pydantic import BaseModel, Field


class CoverageCreate(BaseModel):
    person_id: UUID
    payer_id: UUID
    payer_plan_id: UUID | None = None
    membership_number: str | None = Field(default=None, max_length=100)
    start_date: date | None = None
    end_date: date | None = None


class CoverageResponse(BaseModel):
    id: UUID
    person_id: UUID
    payer_id: UUID
    payer_plan_id: UUID | None
    membership_number: str | None
    start_date: date | None
    end_date: date | None
    verification_status: str
    status: str
