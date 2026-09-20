"""Public trust response schemas."""

from pydantic import BaseModel, Field


class PublicFacilityCard(BaseModel):
    facility_code: str
    name: str
    facility_type: str
    county: str | None = None
    sub_county: str | None = None
    phone: str | None = None
    # Email omitted from public directory by default for spam/abuse control


class TrustPrinciples(BaseModel):
    title: str
    principles: list[str]
    data_protection: list[str]
    patient_rights: list[str]
    government_alignment: list[str]
    developer: str
    copyright_notice: str


class PublicStatus(BaseModel):
    service: str
    status: str
    version: str
    environment_label: str  # never expose internal hostnames
    standalone_first: bool = True
    sha_integrated_not_clone: bool = True


class Attribution(BaseModel):
    product: str = "AfyaSync"
    developed_by: str = "BAHATI GAD WANGWE"
    year: int = 2026
    notice: str
    prohibited: list[str]


class PublicTrustBundle(BaseModel):
    status: PublicStatus
    attribution: Attribution
    principles_summary: str
    facility_count_active: int = Field(ge=0)
    endpoints: list[str]
