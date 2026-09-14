from datetime import date
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class SHAEligibilityRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    person_id: UUID
    membership_number: str = Field(min_length=1, max_length=100)

    @model_validator(mode="after")
    def normalize_membership(self):
        self.membership_number = self.membership_number.strip().upper()
        if not self.membership_number:
            raise ValueError("MEMBERSHIP_NUMBER_REQUIRED")
        return self


class SHAEligibilityResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    coverage_id: UUID | None
    person_id: UUID
    payer_id: UUID
    payer_plan_id: UUID | None
    membership_number: str
    eligible: bool
    verification_status: str = Field(min_length=1, max_length=30)
    start_date: date | None
    end_date: date | None
    external_reference: str | None = Field(default=None, max_length=150)
    checked_at: str
