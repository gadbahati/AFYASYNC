"""Hospital OS journey and integrity schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class StageStatus(BaseModel):
    code: str
    label: str
    complete: bool
    count: int = 0
    notes: list[str] = Field(default_factory=list)


class EncounterJourney(BaseModel):
    encounter_id: UUID
    patient_id: UUID
    facility_id: UUID
    status: str
    stages: list[StageStatus]
    next_recommended: str | None
    blockers: list[str]
    integrity_ok: bool


class OrphanFinding(BaseModel):
    resource_type: str
    resource_id: str
    issue: str
    severity: str  # BLOCKER | WARNING


class FacilityIntegrityReport(BaseModel):
    facility_id: UUID
    scanned_at: datetime
    encounters_checked: int
    findings: list[OrphanFinding]
    integrity_ok: bool
    summary: str
