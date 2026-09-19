from datetime import date
from uuid import UUID
from pydantic import BaseModel, Field

class FHIRPatientName(BaseModel):
    family: str | None = None
    given: list[str] = Field(default_factory=list)

class FHIRPatientResource(BaseModel):
    resourceType: str = "Patient"
    id: UUID
    meta: dict[str, object] = Field(default_factory=dict)
    active: bool
    name: list[FHIRPatientName] = Field(default_factory=list)
    gender: str | None = None
    birthDate: date | None = None
    telecom: list[dict[str, str]] = Field(default_factory=list)
    identifier: list[dict[str, str]] = Field(default_factory=list)
