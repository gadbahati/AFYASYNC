"""Seed default sensitive disease categories.

These categories flag diagnoses that require explicit patient digital consent
before the information can be shared across facilities.
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.consent.models import SensitiveCategory

DEFAULT_CATEGORIES = [
    {
        "code": "HIV",
        "name": "HIV / AIDS related",
        "description": "HIV status, ART, and related conditions. Requires explicit patient consent for cross-facility sharing.",
    },
    {
        "code": "MENTAL_HEALTH",
        "name": "Mental health",
        "description": "Psychiatric diagnoses, counselling notes, and mental health treatment.",
    },
    {
        "code": "STI",
        "name": "Sexually transmitted infections",
        "description": "Sensitive STI diagnoses that patients may prefer to keep facility-local.",
    },
    {
        "code": "GBV",
        "name": "Gender-based violence related",
        "description": "Clinical findings related to gender-based violence or sexual assault.",
    },
    {
        "code": "SUBSTANCE",
        "name": "Substance use disorders",
        "description": "Alcohol, drug, and other substance use related diagnoses.",
    },
]


def seed_sensitive_categories(db: Session) -> list[SensitiveCategory]:
    """Idempotently create the default sensitive categories."""
    created: list[SensitiveCategory] = []
    for item in DEFAULT_CATEGORIES:
        existing = db.scalar(
            select(SensitiveCategory).where(SensitiveCategory.code == item["code"])
        )
        if existing is None:
            cat = SensitiveCategory(
                code=item["code"],
                name=item["name"],
                description=item["description"],
                is_active=True,
            )
            db.add(cat)
            created.append(cat)
    if created:
        db.flush()
    return created
