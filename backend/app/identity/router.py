"""Identity Confidence Engine + membership/household APIs."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_facility_context, require_permission
from app.database import get_db
from app.identity.confidence_service import evaluate_identity_match
from app.identity.schemas import (
    ContributionCreate,
    DeceasedMarkRequest,
    HouseholdCreate,
    HouseholdMemberAdd,
    HouseholdResponse,
    IdentityCorrectionCreate,
    IdentityCorrectionReview,
    IdentityMatchResponse,
    IdentityProbe,
    MembershipCreate,
    MembershipResponse,
)
from app.identity.service import (
    add_contribution,
    add_household_member,
    create_household,
    create_membership,
    list_memberships,
    mark_deceased,
    request_identity_correction,
    review_identity_correction,
)
from app.rbac.models import User

router = APIRouter(prefix="/api/v1/identity", tags=["Identity & Membership"])

IDENTITY_READ = "patients.search"
IDENTITY_WRITE = "patients.create"
IDENTITY_MANAGE = "patients.record.write"


def _err(exc: ValueError) -> HTTPException:
    code = str(exc)
    mapping = {
        "PERSON_NOT_FOUND": 404,
        "PERSON_DECEASED": 409,
        "HOUSEHOLD_NOT_FOUND": 404,
        "ALREADY_IN_HOUSEHOLD": 409,
        "PERSON_IN_OTHER_HOUSEHOLD": 409,
        "HEAD_ALREADY_SET": 400,
        "MEMBERSHIP_NOT_FOUND": 404,
        "ALREADY_DECEASED": 409,
        "FIELD_NOT_CORRECTABLE": 400,
        "CORRECTION_NOT_FOUND": 404,
        "CORRECTION_NOT_PENDING": 409,
        "CANNOT_SELF_APPROVE": 403,
        "CORRECTION_VALUE_MISSING": 400,
        "IDENTITY_MATCH_BLOCK": 409,
        "IDENTITY_MATCH_REVIEW_REQUIRED": 409,
    }
    return HTTPException(status_code=mapping.get(code, 400), detail={"code": code, "message": code})


@router.post("/match", response_model=IdentityMatchResponse)
def identity_match(
    payload: IdentityProbe,
    db: Session = Depends(get_db),
    facility_id: UUID = Depends(get_facility_context),
    user: User = Depends(require_permission(IDENTITY_READ)),
) -> IdentityMatchResponse:
    """Identity Confidence Engine — explainable candidates before create."""
    result = evaluate_identity_match(
        db, payload, facility_id=facility_id, actor_user_id=user.id, persist_log=True
    )
    db.commit()
    return result


@router.post("/households", response_model=HouseholdResponse, status_code=status.HTTP_201_CREATED)
def household_create(
    payload: HouseholdCreate,
    db: Session = Depends(get_db),
    facility_id: UUID = Depends(get_facility_context),
    user: User = Depends(require_permission(IDENTITY_WRITE)),
) -> HouseholdResponse:
    try:
        out = create_household(db, payload, actor_user_id=user.id, facility_id=facility_id)
        db.commit()
        return out
    except ValueError as e:
        raise _err(e) from e


@router.post("/households/{household_id}/members", status_code=status.HTTP_201_CREATED)
def household_add_member(
    household_id: UUID,
    payload: HouseholdMemberAdd,
    db: Session = Depends(get_db),
    facility_id: UUID = Depends(get_facility_context),
    user: User = Depends(require_permission(IDENTITY_WRITE)),
):
    try:
        m = add_household_member(
            db, household_id, payload, actor_user_id=user.id, facility_id=facility_id
        )
        db.commit()
        return {
            "id": str(m.id),
            "person_id": str(m.person_id),
            "relationship_to_head": m.relationship_to_head,
            "is_dependant": m.is_dependant,
        }
    except ValueError as e:
        raise _err(e) from e


@router.post("/memberships", response_model=MembershipResponse, status_code=status.HTTP_201_CREATED)
def membership_create(
    payload: MembershipCreate,
    db: Session = Depends(get_db),
    facility_id: UUID = Depends(get_facility_context),
    user: User = Depends(require_permission(IDENTITY_WRITE)),
) -> MembershipResponse:
    try:
        out = create_membership(db, payload, actor_user_id=user.id, facility_id=facility_id)
        db.commit()
        return out
    except ValueError as e:
        raise _err(e) from e


@router.get("/memberships/person/{person_id}", response_model=list[MembershipResponse])
def membership_list(
    person_id: UUID,
    db: Session = Depends(get_db),
    facility_id: UUID = Depends(get_facility_context),
    user: User = Depends(require_permission(IDENTITY_READ)),
) -> list[MembershipResponse]:
    _ = facility_id
    rows = list_memberships(db, person_id)
    return [
        MembershipResponse(
            id=r.id,
            person_id=r.person_id,
            payer_id=r.payer_id,
            membership_number=r.membership_number,
            status=r.status,
            scheme_code=r.scheme_code,
            employer_name=r.employer_name,
            effective_from=r.effective_from,
            effective_to=r.effective_to,
        )
        for r in rows
    ]


@router.post("/contributions", status_code=status.HTTP_201_CREATED)
def contribution_add(
    payload: ContributionCreate,
    db: Session = Depends(get_db),
    facility_id: UUID = Depends(get_facility_context),
    user: User = Depends(require_permission(IDENTITY_WRITE)),
):
    try:
        e = add_contribution(db, payload, actor_user_id=user.id, facility_id=facility_id)
        db.commit()
        return {
            "id": str(e.id),
            "membership_id": str(e.membership_id),
            "period_label": e.period_label,
            "amount": str(e.amount),
            "currency": e.currency,
        }
    except ValueError as e:
        raise _err(e) from e


@router.post("/deceased")
def deceased_mark(
    payload: DeceasedMarkRequest,
    db: Session = Depends(get_db),
    facility_id: UUID = Depends(get_facility_context),
    user: User = Depends(require_permission(IDENTITY_MANAGE)),
):
    try:
        p = mark_deceased(
            db,
            person_id=payload.person_id,
            date_of_death=payload.date_of_death,
            reason=payload.reason,
            actor_user_id=user.id,
            facility_id=facility_id,
        )
        db.commit()
        return {"person_id": str(p.id), "status": p.status}
    except ValueError as e:
        raise _err(e) from e


@router.post("/corrections", status_code=status.HTTP_201_CREATED)
def correction_request(
    payload: IdentityCorrectionCreate,
    db: Session = Depends(get_db),
    facility_id: UUID = Depends(get_facility_context),
    user: User = Depends(require_permission(IDENTITY_MANAGE)),
):
    try:
        c = request_identity_correction(
            db,
            person_id=payload.person_id,
            field_name=payload.field_name,
            new_value=payload.new_value,
            reason=payload.reason,
            actor_user_id=user.id,
            facility_id=facility_id,
        )
        db.commit()
        return {"id": str(c.id), "status": c.status, "field_name": c.field_name}
    except ValueError as e:
        raise _err(e) from e


@router.post("/corrections/{correction_id}/review")
def correction_review(
    correction_id: UUID,
    payload: IdentityCorrectionReview,
    db: Session = Depends(get_db),
    facility_id: UUID = Depends(get_facility_context),
    user: User = Depends(require_permission(IDENTITY_MANAGE)),
):
    try:
        c = review_identity_correction(
            db,
            correction_id,
            decision=payload.decision,
            actor_user_id=user.id,
            facility_id=facility_id,
        )
        db.commit()
        return {"id": str(c.id), "status": c.status}
    except ValueError as e:
        raise _err(e) from e
