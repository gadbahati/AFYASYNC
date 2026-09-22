"""Identity Confidence Engine — explainable match evidence, never blind create."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit.service import record_audit
from app.coverage.models import Coverage
from app.identity.models import IdentityMatchLog
from app.identity.schemas import (
    IdentityCandidate,
    IdentityMatchResponse,
    IdentityProbe,
    MatchEvidence,
)
from app.patients.models import AfyaIdentity, Person
from app.patients.service import _hash_id_number, _normalize_id_number

# Score thresholds
BLOCK_SCORE = 90  # almost certainly same person — do not create duplicate
REVIEW_SCORE = 55  # possible match — require explicit link/review


def _norm_name(value: str | None) -> str:
    return " ".join((value or "").casefold().split())


def evaluate_identity_match(
    db: Session,
    probe: IdentityProbe,
    *,
    facility_id: UUID | None,
    actor_user_id: UUID | None,
    persist_log: bool = True,
) -> IdentityMatchResponse:
    """Return CLEAR / REVIEW / BLOCK with explainable evidence per candidate."""
    candidates: dict[UUID, IdentityCandidate] = {}

    def _bump(
        person: Person,
        afya_id: str | None,
        code: str,
        weight: int,
        detail: str,
    ) -> None:
        if person.status == "DECEASED":
            # Still surface deceased matches so staff do not re-register the dead
            weight = max(weight, 40)
            detail = f"{detail} (person marked DECEASED)"
        existing = candidates.get(person.id)
        evidence = MatchEvidence(code=code, weight=weight, detail=detail)
        if existing is None:
            score = weight
            candidates[person.id] = IdentityCandidate(
                person_id=person.id,
                afya_id=afya_id,
                first_name=person.first_name,
                last_name=person.last_name,
                date_of_birth=person.date_of_birth,
                status=person.status,
                score=score,
                confidence="LOW",
                evidence=[evidence],
            )
        else:
            # Avoid double-counting same evidence code
            if any(e.code == code for e in existing.evidence):
                return
            existing.evidence.append(evidence)
            existing.score += weight

    # --- Exact national ID hash ---
    if probe.national_id_number:
        try:
            id_hash = _hash_id_number(probe.national_id_number)
        except ValueError:
            id_hash = None
        if id_hash:
            person = db.scalar(select(Person).where(Person.national_id_hash == id_hash))
            if person:
                ident = db.scalar(
                    select(AfyaIdentity).where(AfyaIdentity.person_id == person.id)
                )
                _bump(
                    person,
                    ident.afya_id if ident else None,
                    "NATIONAL_ID_EXACT",
                    100,
                    "National ID hash matches an existing person",
                )

    # --- Afya ID ---
    if probe.afya_id:
        aid = " ".join(probe.afya_id.split()).upper()
        ident = db.scalar(select(AfyaIdentity).where(AfyaIdentity.afya_id == aid))
        if ident:
            person = db.get(Person, ident.person_id)
            if person:
                _bump(
                    person,
                    ident.afya_id,
                    "AFYA_ID_EXACT",
                    100,
                    "Afya ID matches existing identity",
                )

    # --- Membership number via coverage ---
    if probe.membership_number:
        mem = probe.membership_number.strip()
        rows = list(
            db.scalars(
                select(Coverage).where(
                    Coverage.membership_number == mem,
                    Coverage.status == "ACTIVE",
                ).limit(5)
            )
        )
        for cov in rows:
            person = db.get(Person, cov.person_id)
            if person:
                ident = db.scalar(
                    select(AfyaIdentity).where(AfyaIdentity.person_id == person.id)
                )
                _bump(
                    person,
                    ident.afya_id if ident else None,
                    "MEMBERSHIP_EXACT",
                    80,
                    "Active coverage membership number match",
                )

    # --- Phone + name ---
    if probe.phone and probe.first_name and probe.last_name:
        phone = probe.phone.strip()
        fn = _norm_name(probe.first_name)
        ln = _norm_name(probe.last_name)
        rows = list(
            db.scalars(
                select(Person).where(Person.phone == phone).limit(20)
            )
        )
        for person in rows:
            if _norm_name(person.first_name) == fn and _norm_name(person.last_name) == ln:
                ident = db.scalar(
                    select(AfyaIdentity).where(AfyaIdentity.person_id == person.id)
                )
                _bump(
                    person,
                    ident.afya_id if ident else None,
                    "PHONE_NAME_EXACT",
                    70,
                    "Same phone with matching first and last name",
                )
            elif _norm_name(person.last_name) == ln:
                ident = db.scalar(
                    select(AfyaIdentity).where(AfyaIdentity.person_id == person.id)
                )
                _bump(
                    person,
                    ident.afya_id if ident else None,
                    "PHONE_SURNAME",
                    45,
                    "Same phone with matching surname",
                )

    # --- DOB + name ---
    if probe.date_of_birth and probe.first_name and probe.last_name:
        fn = _norm_name(probe.first_name)
        ln = _norm_name(probe.last_name)
        rows = list(
            db.scalars(
                select(Person)
                .where(Person.date_of_birth == probe.date_of_birth)
                .limit(30)
            )
        )
        for person in rows:
            if _norm_name(person.first_name) == fn and _norm_name(person.last_name) == ln:
                ident = db.scalar(
                    select(AfyaIdentity).where(AfyaIdentity.person_id == person.id)
                )
                _bump(
                    person,
                    ident.afya_id if ident else None,
                    "DOB_NAME_EXACT",
                    65,
                    "Same date of birth with matching full name",
                )

    ranked = sorted(candidates.values(), key=lambda c: c.score, reverse=True)
    for c in ranked:
        if c.score >= BLOCK_SCORE:
            c.confidence = "HIGH"
        elif c.score >= REVIEW_SCORE:
            c.confidence = "MEDIUM"
        else:
            c.confidence = "LOW"

    top = ranked[0].score if ranked else 0
    if top >= BLOCK_SCORE:
        outcome = "BLOCK"
        allow = False
        guidance = (
            "High-confidence identity match. Do not create a new person. "
            "Open the existing Afya ID or request an authorised identity link."
        )
    elif top >= REVIEW_SCORE:
        outcome = "REVIEW"
        allow = False
        guidance = (
            "Possible match. Review candidates and evidence before creating. "
            "Creating without review risks duplicate national records."
        )
    else:
        outcome = "CLEAR"
        allow = True
        guidance = "No strong identity match. Registration may proceed."

    if persist_log:
        log = IdentityMatchLog(
            facility_id=facility_id,
            actor_user_id=actor_user_id,
            outcome=outcome,
            top_score=top,
            evidence_json=[
                {"person_id": str(c.person_id), "score": c.score, "codes": [e.code for e in c.evidence]}
                for c in ranked[:10]
            ],
            candidate_person_ids=[str(c.person_id) for c in ranked[:10]],
        )
        db.add(log)
        record_audit(
            db,
            action="IDENTITY_CONFIDENCE_EVAL",
            resource_type="IDENTITY",
            resource_id=str(facility_id) if facility_id else "national",
            result=outcome,
            user_id=actor_user_id,
            facility_id=facility_id,
            metadata={"top_score": top, "candidate_count": len(ranked)},
            commit=False,
        )

    return IdentityMatchResponse(
        outcome=outcome,
        top_score=top,
        candidates=ranked[:10],
        guidance=guidance,
        allow_create=allow,
    )


def assert_clear_to_create(
    db: Session,
    probe: IdentityProbe,
    *,
    facility_id: UUID | None,
    actor_user_id: UUID | None,
    force_reason: str | None = None,
) -> IdentityMatchResponse:
    """Raise if create should be blocked. force_reason only for privileged override path."""
    result = evaluate_identity_match(
        db, probe, facility_id=facility_id, actor_user_id=actor_user_id, persist_log=True
    )
    if result.outcome == "BLOCK":
        raise ValueError("IDENTITY_MATCH_BLOCK")
    if result.outcome == "REVIEW":
        reason = (force_reason or "").strip()
        if len(reason) < 20:
            raise ValueError("IDENTITY_MATCH_REVIEW_REQUIRED")
        record_audit(
            db,
            action="IDENTITY_CREATE_OVERRIDE",
            resource_type="IDENTITY",
            resource_id=str(facility_id) if facility_id else "national",
            result="OVERRIDE",
            user_id=actor_user_id,
            facility_id=facility_id,
            metadata={"reason_length": len(reason), "top_score": result.top_score},
            commit=False,
        )
    return result
