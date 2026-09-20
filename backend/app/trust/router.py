"""Unauthenticated public trust endpoints — hardened, no PHI."""

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.trust.schemas import (
    Attribution,
    PublicFacilityCard,
    PublicStatus,
    PublicTrustBundle,
    TrustPrinciples,
)
from app.trust.service import (
    attribution,
    list_public_facilities,
    public_status,
    trust_bundle,
    trust_principles,
)

router = APIRouter(prefix="/api/v1/public", tags=["Public Trust"])

# Simple in-process rate note: rely on edge/WAF in production; responses are cacheable.


@router.get("/trust", response_model=PublicTrustBundle)
def get_trust_bundle(db: Session = Depends(get_db)) -> PublicTrustBundle:
    """Single entry point for public trust metadata."""
    return trust_bundle(db)


@router.get("/status", response_model=PublicStatus)
def get_public_status() -> PublicStatus:
    return public_status()


@router.get("/attribution", response_model=Attribution)
def get_attribution() -> Attribution:
    return attribution()


@router.get("/principles", response_model=TrustPrinciples)
def get_principles() -> TrustPrinciples:
    return trust_principles()


@router.get("/privacy")
def get_privacy_summary() -> dict:
    """Plain-language privacy summary for the public (not legal advice)."""
    p = trust_principles()
    return {
        "title": "AfyaSync Privacy Summary",
        "data_protection": p.data_protection,
        "patient_rights": p.patient_rights,
        "note": (
            "This summary does not replace the facility privacy notice or legal counsel. "
            "Patients should use the portal and facility channels for access requests."
        ),
        "developer": p.developer,
        "copyright_notice": p.copyright_notice,
    }


@router.get("/facilities", response_model=list[PublicFacilityCard])
def get_public_facilities(
    request: Request,
    county: str | None = Query(default=None, max_length=100),
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
) -> list[PublicFacilityCard]:
    """Active facility directory — no patient data, no emails by default."""
    _ = request  # reserved for future edge rate-limit keys
    return list_public_facilities(db, county=county, limit=limit)
