from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class NationalRecordLocatorRequest(BaseModel):
    """Explicit purpose is required before a national record-footprint lookup."""

    model_config = ConfigDict(extra="forbid")

    afya_id: str = Field(min_length=1, max_length=20)
    access_reason: str = Field(min_length=5, max_length=500)


class NationalRecordFacility(BaseModel):
    """Minimum facility metadata needed to route an authorised continuity request."""

    model_config = ConfigDict(from_attributes=True)

    facility_id: UUID
    facility_code: str = Field(min_length=1, max_length=32)
    facility_name: str = Field(min_length=1, max_length=200)
    county: str | None = Field(default=None, max_length=100)
    enrollment_status: str = Field(min_length=1, max_length=30)


class NationalRecordLocatorResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    afya_id: str = Field(min_length=1, max_length=20)
    person_id: UUID
    record_status: str = Field(min_length=1, max_length=30)
    facilities: list[NationalRecordFacility]
