from pydantic import BaseModel, ConfigDict, Field


class NationalReferralAging(BaseModel):
    bucket: str
    count: int = Field(ge=0)

    model_config = ConfigDict(extra="forbid")


class NationalReferralRouteMetric(BaseModel):
    source_facility_id: str
    source_facility_code: str
    source_facility_name: str
    destination_facility_id: str
    destination_facility_code: str
    destination_facility_name: str
    total: int = Field(ge=0)
    active: int = Field(ge=0)
    completed: int = Field(ge=0)
    declined: int = Field(ge=0)

    model_config = ConfigDict(extra="forbid")


class NationalReferralMetricsResponse(BaseModel):
    total: int = Field(ge=0)
    active: int = Field(ge=0)
    completed: int = Field(ge=0)
    declined: int = Field(ge=0)
    acceptance_rate: float = Field(ge=0, le=100)
    completion_rate: float = Field(ge=0, le=100)
    aging: list[NationalReferralAging]
    routes: list[NationalReferralRouteMetric]

    model_config = ConfigDict(extra="forbid")
