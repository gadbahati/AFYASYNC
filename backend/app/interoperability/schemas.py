from datetime import date
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class FHIRIdentifier(BaseModel):
    system: str = Field(min_length=1, max_length=200)
    value: str = Field(min_length=1, max_length=200)


class FHIRHumanName(BaseModel):
    use: str = "official"
    family: str = Field(min_length=1, max_length=100)
    given: list[str] = Field(default_factory=list, max_length=3)


class FHIRPatientResource(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    resourceType: str = "Patient"
    id: UUID
    identifier: list[FHIRIdentifier] = Field(default_factory=list, max_length=3)
    name: list[FHIRHumanName] = Field(default_factory=list, max_length=1)
    birthDate: date | None = None
    gender: str | None = None
    active: bool


class FHIRCapabilityResponse(BaseModel):
    resourceType: str = "CapabilityStatement"
    id: str = "afasync"
    status: str = "active"
    kind: str = "instance"
    fhirVersion: str = "R4"
    format: list[str] = Field(default_factory=lambda: ["json"])
    patient_read: bool = True
    clinical_read: bool = True
    clinical_write: bool = False
    supported_resources: list[str] = Field(default_factory=lambda: ["Patient", "AllergyIntolerance", "Bundle"], max_length=20)
    profiles: list[str] = Field(default_factory=lambda: [
        "http://hl7.org/fhir/StructureDefinition/Patient",
        "http://hl7.org/fhir/StructureDefinition/AllergyIntolerance",
    ], max_length=20)
    dhis2_api_version: str = "2.40"
    identifier_systems: list[str] = Field(default_factory=lambda: ["https://afasync.health.go.ke/identifier/afya-id"], max_length=10)
