from pydantic import BaseModel, ConfigDict, Field


class NationalCapacityFacility(BaseModel):
    facility_id: str
    facility_code: str
    facility_name: str
    county: str | None
    departments: int = Field(ge=0)
    scheduled_appointments: int = Field(ge=0)
    waiting_queue_entries: int = Field(ge=0)

    model_config = ConfigDict(extra="forbid")


class NationalCapacityResponse(BaseModel):
    active_facilities: int = Field(ge=0)
    active_departments: int = Field(ge=0)
    scheduled_appointments: int = Field(ge=0)
    waiting_queue_entries: int = Field(ge=0)
    facilities: list[NationalCapacityFacility]

    model_config = ConfigDict(extra="forbid")
