from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class FHIREncounterResource(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    resourceType: str = "Encounter"
    id: UUID
    status: str = Field(min_length=1, max_length=30)
    class_code: str = Field(min_length=1, max_length=30)
    period_start: datetime
    period_end: datetime | None = None
    patient_id: UUID


class FHIRBundleEntry(BaseModel):
    fullUrl: str = Field(min_length=1, max_length=500)
    resource: object


class FHIRBundleResource(BaseModel):
    resourceType: str = "Bundle"
    type: str = "searchset"
    total: int = Field(ge=0, le=101)
    entry: list[FHIRBundleEntry] = Field(default_factory=list, max_length=101)
