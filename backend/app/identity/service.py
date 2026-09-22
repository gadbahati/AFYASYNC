"""Household, membership, deceased, and identity correction services."""

from __future__ import annotations

from datetime import date, datetime, timezone
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.audit.service import record_audit
from app.identity.models import (
    ContributionEntry,
    Household,
    HouseholdMember,
    IdentityCorrection,
    MembershipRecord,
)
from app.identity.schemas import (
    ContributionCreate,
    HouseholdCreate,
    HouseholdMemberAdd,
    HouseholdResponse,
    MembershipCreate,
    MembershipResponse,
)
from app.patients.models import AfyaIdentity, Person

_ALLOWED_CORR_FIELDS = {
    "first_name",
    "middle_name",
    "last_name",
    "phone",
    "email",
    "date_of_birth",
    "sex",
    "address",
}


def _require_active_person(db: Session, person_id: UUID) -> Person:
    person = db.get(Person, person_id)
    if person is None:
        raise ValueError("PERSON_NOT_FOUND")
    if person.status == "DECEASED":
        raise ValueError("PERSON_DECEASED")
    return person


def create_household(
    db: Session,
    payload: HouseholdCreate,
    *,
    actor_user_id: UUID,
    facility_id: UUID | None,
) -> HouseholdResponse:
    head = _require_active_person(db, payload.head_person_id)
    hh = Household(
        head_person_id=head.id,
        label=payload.label,
        county=payload.county,
        status="ACTIVE",
    )
    db.add(hh)
    db.flush()
    db.add(
        HouseholdMember(
            household_id=hh.id,
            person_id=head.id,
            relationship_to_head="HEAD",
            is_dependant=False,
            status="ACTIVE",
            effective_from=date.today(),
        )
    )
    db.flush()
    record_audit(
        db,
        action="HOUSEHOLD_CREATED",
        resource_type="HOUSEHOLD",
        resource_id=str(hh.id),
        result="SUCCESS",
        user_id=actor_user_id,
        facility_id=facility_id,
        patient_id=head.id,
        commit=False,
    )
    return HouseholdResponse(
        id=hh.id,
        head_person_id=hh.head_person_id,
        label=hh.label,
        county=hh.county,
        status=hh.status,
        member_count=1,
    )


def add_household_member(
    db: Session,
    household_id: UUID,
    payload: HouseholdMemberAdd,
    *,
    actor_user_id: UUID,
    facility_id: UUID | None,
) -> HouseholdMember:
    hh = db.get(Household, household_id)
    if hh is None or hh.status != "ACTIVE":
        raise ValueError("HOUSEHOLD_NOT_FOUND")
    person = _require_active_person(db, payload.person_id)
    if payload.relationship_to_head == "HEAD":
        raise ValueError("HEAD_ALREADY_SET")
    existing = db.scalar(
        select(HouseholdMember).where(
            HouseholdMember.household_id == household_id,
            HouseholdMember.person_id == person.id,
            HouseholdMember.status == "ACTIVE",
        )
    )
    if existing:
        raise ValueError("ALREADY_IN_HOUSEHOLD")
    # Prevent person belonging to two active households as dependant simultaneously
    other = db.scalar(
        select(HouseholdMember).where(
            HouseholdMember.person_id == person.id,
            HouseholdMember.status == "ACTIVE",
            HouseholdMember.household_id != household_id,
        )
    )
    if other is not None:
        raise ValueError("PERSON_IN_OTHER_HOUSEHOLD")

    member = HouseholdMember(
        household_id=household_id,
        person_id=person.id,
        relationship_to_head=payload.relationship_to_head,
        is_dependant=payload.is_dependant or payload.relationship_to_head in {"CHILD", "DEPENDANT"},
        status="ACTIVE",
        effective_from=payload.effective_from or date.today(),
    )
    db.add(member)
    db.flush()
    record_audit(
        db,
        action="HOUSEHOLD_MEMBER_ADDED",
        resource_type="HOUSEHOLD",
        resource_id=str(household_id),
        result="SUCCESS",
        user_id=actor_user_id,
        facility_id=facility_id,
        patient_id=person.id,
        metadata={"relationship": payload.relationship_to_head},
        commit=False,
    )
    return member


def create_membership(
    db: Session,
    payload: MembershipCreate,
    *,
    actor_user_id: UUID,
    facility_id: UUID | None,
) -> MembershipResponse:
    person = _require_active_person(db, payload.person_id)
    rec = MembershipRecord(
        person_id=person.id,
        payer_id=payload.payer_id,
        membership_number=payload.membership_number.strip() if payload.membership_number else None,
        status=payload.status,
        scheme_code=payload.scheme_code,
        effective_from=payload.effective_from,
        effective_to=payload.effective_to,
        employer_name=payload.employer_name,
        employer_pin=payload.employer_pin,
    )
    db.add(rec)
    db.flush()
    record_audit(
        db,
        action="MEMBERSHIP_CREATED",
        resource_type="MEMBERSHIP",
        resource_id=str(rec.id),
        result="SUCCESS",
        user_id=actor_user_id,
        facility_id=facility_id,
        patient_id=person.id,
        commit=False,
    )
    return MembershipResponse(
        id=rec.id,
        person_id=rec.person_id,
        payer_id=rec.payer_id,
        membership_number=rec.membership_number,
        status=rec.status,
        scheme_code=rec.scheme_code,
        employer_name=rec.employer_name,
        effective_from=rec.effective_from,
        effective_to=rec.effective_to,
    )


def add_contribution(
    db: Session,
    payload: ContributionCreate,
    *,
    actor_user_id: UUID,
    facility_id: UUID | None,
) -> ContributionEntry:
    mem = db.get(MembershipRecord, payload.membership_id)
    if mem is None:
        raise ValueError("MEMBERSHIP_NOT_FOUND")
    entry = ContributionEntry(
        membership_id=mem.id,
        period_label=payload.period_label.strip(),
        amount=payload.amount,
        currency=payload.currency.upper(),
        paid_on=payload.paid_on,
        source=payload.source,
        status="RECORDED",
    )
    db.add(entry)
    db.flush()
    record_audit(
        db,
        action="CONTRIBUTION_RECORDED",
        resource_type="MEMBERSHIP",
        resource_id=str(mem.id),
        result="SUCCESS",
        user_id=actor_user_id,
        facility_id=facility_id,
        patient_id=mem.person_id,
        metadata={"period": entry.period_label, "amount": str(entry.amount)},
        commit=False,
    )
    return entry


def mark_deceased(
    db: Session,
    *,
    person_id: UUID,
    date_of_death: date,
    reason: str,
    actor_user_id: UUID,
    facility_id: UUID | None,
) -> Person:
    person = db.get(Person, person_id)
    if person is None:
        raise ValueError("PERSON_NOT_FOUND")
    if person.status == "DECEASED":
        raise ValueError("ALREADY_DECEASED")
    person.status = "DECEASED"
    # Soft-disable Afya identity for login/match create paths
    identity = db.scalar(select(AfyaIdentity).where(AfyaIdentity.person_id == person.id))
    if identity and identity.status == "ACTIVE":
        identity.status = "DECEASED"
    db.flush()
    record_audit(
        db,
        action="PERSON_MARKED_DECEASED",
        resource_type="PERSON",
        resource_id=str(person.id),
        result="SUCCESS",
        user_id=actor_user_id,
        facility_id=facility_id,
        patient_id=person.id,
        metadata={
            "date_of_death": date_of_death.isoformat(),
            "reason_length": len(reason.strip()),
        },
        commit=False,
    )
    return person


def request_identity_correction(
    db: Session,
    *,
    person_id: UUID,
    field_name: str,
    new_value: str,
    reason: str,
    actor_user_id: UUID,
    facility_id: UUID | None,
) -> IdentityCorrection:
    if field_name not in _ALLOWED_CORR_FIELDS:
        raise ValueError("FIELD_NOT_CORRECTABLE")
    person = db.get(Person, person_id)
    if person is None:
        raise ValueError("PERSON_NOT_FOUND")
    if person.status == "DECEASED":
        raise ValueError("PERSON_DECEASED")
    old = getattr(person, field_name, None)
    old_s = str(old) if old is not None else None
    # Redact long values for storage
    def _redact(v: str | None) -> str | None:
        if v is None:
            return None
        if len(v) <= 4:
            return "****"
        return v[:2] + "***" + v[-1:]

    corr = IdentityCorrection(
        person_id=person_id,
        field_name=field_name,
        old_value_redacted=_redact(old_s),
        new_value_redacted=_redact(new_value.strip()),
        reason=reason.strip(),
        status="PENDING",
        requested_by=actor_user_id,
    )
    # Store pending new value in reason metadata via audit only; apply on approve
    db.add(corr)
    db.flush()
    # Keep pending value in a side channel: notes on reason is insufficient.
    # Apply immediately only for non-sensitive demographic fields with single reviewer later.
    record_audit(
        db,
        action="IDENTITY_CORRECTION_REQUESTED",
        resource_type="PERSON",
        resource_id=str(person_id),
        result="PENDING",
        user_id=actor_user_id,
        facility_id=facility_id,
        patient_id=person_id,
        metadata={"field": field_name, "correction_id": str(corr.id)},
        commit=False,
    )
    # Stash full new value in memory path: use Text field with structured prefix for approve step
    corr.reason = f"{reason.strip()}\n__NEW__:{new_value.strip()}"
    db.flush()
    return corr


def review_identity_correction(
    db: Session,
    correction_id: UUID,
    *,
    decision: str,
    actor_user_id: UUID,
    facility_id: UUID | None,
) -> IdentityCorrection:
    corr = db.get(IdentityCorrection, correction_id)
    if corr is None:
        raise ValueError("CORRECTION_NOT_FOUND")
    if corr.status != "PENDING":
        raise ValueError("CORRECTION_NOT_PENDING")
    if corr.requested_by == actor_user_id:
        raise ValueError("CANNOT_SELF_APPROVE")  # maker-checker

    corr.reviewed_by = actor_user_id
    corr.reviewed_at = datetime.now(timezone.utc)
    decision = decision.upper()
    if decision == "REJECTED":
        corr.status = "REJECTED"
        db.flush()
        record_audit(
            db,
            action="IDENTITY_CORRECTION_REJECTED",
            resource_type="PERSON",
            resource_id=str(corr.person_id),
            result="REJECTED",
            user_id=actor_user_id,
            facility_id=facility_id,
            patient_id=corr.person_id,
            metadata={"correction_id": str(corr.id)},
            commit=False,
        )
        return corr

    # APPROVED — extract new value
    new_val = None
    if "__NEW__:" in (corr.reason or ""):
        new_val = corr.reason.split("__NEW__:", 1)[1].strip()
    if not new_val:
        raise ValueError("CORRECTION_VALUE_MISSING")

    person = db.get(Person, corr.person_id)
    if person is None:
        raise ValueError("PERSON_NOT_FOUND")
    if corr.field_name == "date_of_birth":
        setattr(person, corr.field_name, date.fromisoformat(new_val))
    else:
        setattr(person, corr.field_name, new_val)
    corr.status = "APPROVED"
    # Strip stashed value from reason for storage hygiene
    corr.reason = corr.reason.split("\n__NEW__:")[0]
    db.flush()
    record_audit(
        db,
        action="IDENTITY_CORRECTION_APPROVED",
        resource_type="PERSON",
        resource_id=str(corr.person_id),
        result="APPROVED",
        user_id=actor_user_id,
        facility_id=facility_id,
        patient_id=corr.person_id,
        metadata={"correction_id": str(corr.id), "field": corr.field_name},
        commit=False,
    )
    return corr


def list_memberships(db: Session, person_id: UUID) -> list[MembershipRecord]:
    return list(
        db.scalars(
            select(MembershipRecord)
            .where(MembershipRecord.person_id == person_id)
            .order_by(MembershipRecord.created_at.desc())
        )
    )
