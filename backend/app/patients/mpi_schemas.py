from datetime import date
from uuid import UUID
from pydantic import BaseModel


class MPICandidate(BaseModel):
    patient_id: UUID
    afya_id: str
    full_name: str
    date_of_birth: date | None
    phone: str | None
    match_score: int
    match_reasons: list[str]


class MPIResponse(BaseModel):
    candidates: list[MPICandidate]
    requires_review_before_registration: bool
