"""Prescribe-time allergy and medication safety schemas."""

from uuid import UUID

from pydantic import BaseModel, Field


class SafetyMedIn(BaseModel):
    medication_id: UUID


class SafetyCheckRequest(BaseModel):
    patient_id: UUID
    encounter_id: UUID | None = None
    medications: list[SafetyMedIn] = Field(min_length=1, max_length=30)


class SafetyConflict(BaseModel):
    code: str
    severity: str  # LOW | MEDIUM | HIGH | CRITICAL
    title: str
    detail: str
    medication_id: UUID | None = None
    medication_name: str | None = None
    allergen: str | None = None
    allergy_id: UUID | None = None
    interacting_medication_id: UUID | None = None
    blocking: bool = False  # if True, prescription must not proceed


class SafetyCheckResponse(BaseModel):
    patient_id: UUID
    facility_id: UUID
    can_prescribe: bool
    blocking_count: int
    warning_count: int
    conflicts: list[SafetyConflict]
    allergy_count_checked: int
    notes: list[str] = Field(default_factory=list)
