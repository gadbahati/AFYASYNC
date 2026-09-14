from datetime import date
from uuid import UUID

from pydantic import BaseModel, Field


class FHIRPatientResource(BaseModel):
    resourceType: str = "Patient"
    id: UUID
    identifier: list[dict[str, str]] = Field(default_factory=list, max_length=3)
    name: list[dict[str, object]] = Field(default_factory=list, max_length=1)
    birthDate: date | None = None
    gender: str | None = None
    active: bool


class FHIRCapabilityResponse(BaseModel):
    resourceType: str = "CapabilityStatement"
    status: str = "active"
    patient_read: bool = True
    clinical_write: bool = False
