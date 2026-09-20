"""Issue and verify consent-aware continuity cards."""

from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit.service import record_audit
from app.clinical.models import Diagnosis
from app.consent.models import SensitiveDiseaseConsent
from app.continuity.models import ContinuityCard
from app.patients.models import AfyaIdentity, Person

TOKEN_BYTES = 24
CARD_TTL_DAYS = 365
MAX_ACTIVE_CARDS = 3


class ContinuityError(ValueError):
    pass


def _hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _new_raw_token() -> str:
    # URL-safe, no padding noise
    return secrets.token_urlsafe(TOKEN_BYTES)


def issue_card(
    db: Session,
    *,
    person_id: UUID,
    actor_user_id: UUID,
) -> tuple[ContinuityCard, str]:
    person = db.get(Person, person_id)
    if person is None or person.status != "ACTIVE":
        raise ContinuityError("PATIENT_NOT_FOUND")

    active = list(
        db.scalars(
            select(ContinuityCard).where(
                ContinuityCard.person_id == person_id,
                ContinuityCard.is_active.is_(True),
            )
        )
    )
    # Soft-revoke oldest if over limit
    if len(active) >= MAX_ACTIVE_CARDS:
        for card in sorted(active, key=lambda c: c.created_at)[: len(active) - MAX_ACTIVE_CARDS + 1]:
            card.is_active = False
            card.revoked_at = datetime.now(timezone.utc)
            card.revoke_reason = "ROTATED"
            db.add(card)

    raw = _new_raw_token()
    now = datetime.now(timezone.utc)
    card = ContinuityCard(
        person_id=person_id,
        token_hash=_hash_token(raw),
        token_prefix=raw[:8],
        is_active=True,
        expires_at=now + timedelta(days=CARD_TTL_DAYS),
        verify_count=0,
    )
    db.add(card)
    db.flush()

    record_audit(
        db,
        action="CONTINUITY_CARD_ISSUED",
        resource_type="ContinuityCard",
        resource_id=str(card.id),
        result="SUCCESS",
        user_id=actor_user_id,
        patient_id=person_id,
        metadata={"prefix": card.token_prefix, "expires_at": card.expires_at.isoformat()},
        commit=False,
    )
    return card, raw


def revoke_card(
    db: Session,
    *,
    person_id: UUID,
    card_id: UUID,
    actor_user_id: UUID,
    reason: str = "PATIENT_REVOKE",
) -> ContinuityCard:
    card = db.get(ContinuityCard, card_id)
    if card is None or card.person_id != person_id:
        raise ContinuityError("CARD_NOT_FOUND")
    if not card.is_active:
        return card
    card.is_active = False
    card.revoked_at = datetime.now(timezone.utc)
    card.revoke_reason = (reason or "REVOKED")[:200]
    db.add(card)
    record_audit(
        db,
        action="CONTINUITY_CARD_REVOKED",
        resource_type="ContinuityCard",
        resource_id=str(card.id),
        result="SUCCESS",
        user_id=actor_user_id,
        patient_id=person_id,
        metadata={"reason": card.revoke_reason},
        commit=False,
    )
    return card


def list_my_cards(db: Session, person_id: UUID) -> list[ContinuityCard]:
    return list(
        db.scalars(
            select(ContinuityCard)
            .where(ContinuityCard.person_id == person_id)
            .order_by(ContinuityCard.created_at.desc())
            .limit(20)
        )
    )


def _find_by_raw(db: Session, raw_token: str) -> ContinuityCard | None:
    raw = (raw_token or "").strip()
    if len(raw) < 16 or len(raw) > 128:
        return None
    return db.scalar(select(ContinuityCard).where(ContinuityCard.token_hash == _hash_token(raw)))


def build_consent_snapshot(db: Session, person_id: UUID, *,
                          include_sensitive_shared: bool = True) -> dict:
    """Build continuity payload. Sensitive diagnoses only if CROSS_FACILITY."""
    person = db.get(Person, person_id)
    if person is None:
        raise ContinuityError("PATIENT_NOT_FOUND")

    identity = db.scalar(select(AfyaIdentity).where(AfyaIdentity.person_id == person_id))

    # Allergies if model exists
    allergies: list[dict] = []
    try:
        from app.patients.allergy_models import Allergy  # type: ignore

        rows = list(
            db.scalars(
                select(Allergy).where(
                    Allergy.patient_id == person_id,
                    Allergy.status == "ACTIVE",
                )
            )
        )
        for a in rows:
            allergies.append(
                {
                    "substance": getattr(a, "substance", None) or getattr(a, "allergen", None),
                    "severity": getattr(a, "severity", None),
                    "reaction": getattr(a, "reaction", None),
                }
            )
    except Exception:
        allergies = []

    diagnoses_out: list[dict] = []
    if include_sensitive_shared:
        dx_rows = list(
            db.scalars(
                select(Diagnosis)
                .where(Diagnosis.patient_id == person_id)
                .order_by(Diagnosis.created_at.desc())
                .limit(40)
            )
        )
        # Map diagnosis_id → consent
        consent_by_dx: dict[UUID, SensitiveDiseaseConsent] = {}
        consents = list(
            db.scalars(
                select(SensitiveDiseaseConsent).where(
                    SensitiveDiseaseConsent.patient_id == person_id
                )
            )
        )
        for c in consents:
            consent_by_dx[c.diagnosis_id] = c

        for dx in dx_rows:
            is_sensitive = bool(getattr(dx, "is_sensitive", False))
            if is_sensitive:
                c = consent_by_dx.get(dx.id)
                if c is None or not c.consent_given or c.share_scope != "CROSS_FACILITY":
                    continue  # blocked — patient did not share
            diagnoses_out.append(
                {
                    "code": getattr(dx, "code", None) or getattr(dx, "icd_code", None),
                    "description": getattr(dx, "description", None)
                    or getattr(dx, "display", None),
                    "sensitive": is_sensitive,
                }
            )

    blood = getattr(person, "blood_type", None) or getattr(person, "blood_group", None)

    return {
        "afya_id": identity.afya_id if identity else None,
        "display_name": f"{(person.first_name or '').strip()} {(person.last_name or '').strip()}".strip()
        or "Patient",
        "sex": person.sex,
        "date_of_birth": person.date_of_birth.isoformat() if person.date_of_birth else None,
        "blood_type": blood,
        "allergies": allergies[:20],
        "shared_diagnoses": diagnoses_out[:15],
        "consent_note": (
            "Sensitive conditions appear only when the patient signed CROSS_FACILITY disclosure."
        ),
    }


def verify_token(
    db: Session,
    *,
    raw_token: str,
    actor_user_id: UUID | None,
    mode: str = "PUBLIC",
) -> dict:
    card = _find_by_raw(db, raw_token)
    if card is None:
        raise ContinuityError("CARD_NOT_FOUND")
    now = datetime.now(timezone.utc)
    if not card.is_active:
        raise ContinuityError("CARD_REVOKED")
    exp = card.expires_at
    if exp.tzinfo is None:
        exp = exp.replace(tzinfo=timezone.utc)
    if exp < now:
        raise ContinuityError("CARD_EXPIRED")

    card.last_verified_at = now
    card.verify_count = int(card.verify_count or 0) + 1
    db.add(card)

    snapshot = build_consent_snapshot(db, card.person_id, include_sensitive_shared=True)

    record_audit(
        db,
        action="CONTINUITY_CARD_VERIFIED",
        resource_type="ContinuityCard",
        resource_id=str(card.id),
        result="SUCCESS",
        user_id=actor_user_id,
        patient_id=card.person_id,
        metadata={"mode": mode, "verify_count": card.verify_count},
        commit=False,
    )

    return {
        "card_id": str(card.id),
        "token_prefix": card.token_prefix,
        "expires_at": card.expires_at.isoformat(),
        "verify_count": card.verify_count,
        "mode": mode,
        "snapshot": snapshot,
    }
