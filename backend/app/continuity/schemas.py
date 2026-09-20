from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class ContinuityCardMeta(BaseModel):
    id: UUID
    token_prefix: str
    is_active: bool
    expires_at: datetime
    last_verified_at: datetime | None = None
    verify_count: int = 0
    created_at: datetime | None = None
    revoked_at: datetime | None = None


class ContinuityCardIssued(BaseModel):
    card: ContinuityCardMeta
    # Shown once — patient must save / print / QR this value
    token: str = Field(min_length=16, max_length=128)
    verify_path: str


class ContinuityCardListResponse(BaseModel):
    items: list[ContinuityCardMeta]
    total: int


class ContinuityVerifyRequest(BaseModel):
    token: str = Field(min_length=16, max_length=128)


class ContinuitySnapshot(BaseModel):
    afya_id: str | None = None
    display_name: str
    sex: str | None = None
    date_of_birth: str | None = None
    blood_type: str | None = None
    allergies: list[dict] = Field(default_factory=list)
    shared_diagnoses: list[dict] = Field(default_factory=list)
    consent_note: str | None = None


class ContinuityVerifyResponse(BaseModel):
    card_id: str
    token_prefix: str
    expires_at: str
    verify_count: int
    mode: str
    snapshot: ContinuitySnapshot
