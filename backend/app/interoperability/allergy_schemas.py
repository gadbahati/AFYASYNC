from datetime import date
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class FHIRCodeableConcept(BaseModel):
    text: str | None = Field(default=None, max_length=500)
    coding: list[dict[str, str]] = Field(default_factory=list, max_length=3)


class FHIRReference(BaseModel):
    reference: str = Field(min_length=1, max_length=200)


class FHIRAllergyReactionManifestation(BaseModel):
    manifestation: FHIRCodeableConcept
    description: str | None = Field(default=None, max_length=1000)


class FHIRAllergyReaction(BaseModel):
    manifestation: list[FHIRCodeableConcept] = Field(min_length=1, max_length=5)
    description: str | None = Field(default=None, max_length=1000)


class FHIRAllergyIntoleranceResource(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    resourceType: str = "AllergyIntolerance"
    id: UUID
    meta: dict[str, object] = Field(default_factory=dict)
    clinicalStatus: FHIRCodeableConcept
    verificationStatus: FHIRCodeableConcept
    criticality: str | None = None
    code: FHIRCodeableConcept
    patient: FHIRReference
    onsetDateTime: date | None = None
    recordedDate: date | None = None
    reaction: list[FHIRAllergyReaction] = Field(default_factory=list, max_length=10)
    note: list[FHIRCodeableConcept] = Field(default_factory=list, max_length=3)
