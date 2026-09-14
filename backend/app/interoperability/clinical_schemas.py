from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class FHIRPeriod(BaseModel):
    start: datetime
    end: datetime | None = None


class FHIREncounterResource(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    resourceType: str = "Encounter"
    id: UUID
    status: str = Field(min_length=1, max_length=30)
    class_code: dict[str, str] = Field(alias="class")
    period: FHIRPeriod | None = None
    patient_id: UUID = Field(exclude=True)
    period_start: datetime | None = Field(default=None, exclude=True)
    period_end: datetime | None = Field(default=None, exclude=True)
    subject: dict[str, str] = Field(default_factory=dict)

    @model_validator(mode="after")
    def build_canonical_fields(self):
        if self.period is None:
            if self.period_start is None:
                raise ValueError("period.start is required")
            self.period = FHIRPeriod(start=self.period_start, end=self.period_end)
        self.subject = {"reference": f"Patient/{self.patient_id}"}
        return self


class FHIRBundleEntry(BaseModel):
    fullUrl: str = Field(min_length=1, max_length=500)
    resource: object


class FHIRBundleResource(BaseModel):
    resourceType: str = "Bundle"
    type: str = "searchset"
    total: int = Field(ge=0, le=101)
    entry: list[FHIRBundleEntry] = Field(default_factory=list, max_length=101)
