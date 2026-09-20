from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_facility_context, require_patient_identity, require_permission
from app.continuity.schemas import (
    ContinuityCardIssued,
    ContinuityCardListResponse,
    ContinuityCardMeta,
    ContinuitySnapshot,
    ContinuityVerifyRequest,
    ContinuityVerifyResponse,
)
from app.continuity.service import (
    ContinuityError,
    issue_card,
    list_my_cards,
    revoke_card,
    verify_token,
)
from app.database import get_db
from app.portal.service import PortalError, require_patient_person_id
from app.rbac.models import User

# Patient-managed routes under portal prefix
portal_router = APIRouter(prefix="/api/v1/portal/continuity-card", tags=["Continuity Card"])

# Public verify (token only — rate-limit at gateway in production)
public_router = APIRouter(prefix="/api/v1/continuity", tags=["Continuity Card"])

# Facility staff scan
facility_router = APIRouter(prefix="/api/v1/facility/continuity", tags=["Continuity Card"])


def _http(err: ContinuityError | PortalError) -> HTTPException:
    code = str(err)
    mapping = {
        "PATIENT_NOT_FOUND": 404,
        "CARD_NOT_FOUND": 404,
        "CARD_REVOKED": 410,
        "CARD_EXPIRED": 410,
        "PATIENT_IDENTITY_REQUIRED": 403,
    }
    return HTTPException(status_code=mapping.get(code, 400), detail=code)


def _meta(card) -> ContinuityCardMeta:
    return ContinuityCardMeta(
        id=card.id,
        token_prefix=card.token_prefix,
        is_active=card.is_active,
        expires_at=card.expires_at,
        last_verified_at=card.last_verified_at,
        verify_count=int(card.verify_count or 0),
        created_at=card.created_at,
        revoked_at=card.revoked_at,
    )


@portal_router.get("", response_model=ContinuityCardListResponse)
def portal_list_cards(
    user: User = Depends(require_patient_identity),
    db: Session = Depends(get_db),
) -> ContinuityCardListResponse:
    try:
        person_id = require_patient_person_id(user.person_id)
    except PortalError as err:
        raise _http(err) from err
    items = list_my_cards(db, person_id)
    return ContinuityCardListResponse(items=[_meta(c) for c in items], total=len(items))


@portal_router.post("/issue", response_model=ContinuityCardIssued)
def portal_issue_card(
    user: User = Depends(require_patient_identity),
    db: Session = Depends(get_db),
) -> ContinuityCardIssued:
    try:
        person_id = require_patient_person_id(user.person_id)
        card, raw = issue_card(db, person_id=person_id, actor_user_id=user.id)
        db.commit()
        db.refresh(card)
    except (ContinuityError, PortalError) as err:
        db.rollback()
        raise _http(err) from err
    return ContinuityCardIssued(
        card=_meta(card),
        token=raw,
        verify_path=f"/continuity/{raw}",
    )


@portal_router.post("/{card_id}/revoke", response_model=ContinuityCardMeta)
def portal_revoke_card(
    card_id: UUID,
    user: User = Depends(require_patient_identity),
    db: Session = Depends(get_db),
) -> ContinuityCardMeta:
    try:
        person_id = require_patient_person_id(user.person_id)
        card = revoke_card(
            db,
            person_id=person_id,
            card_id=card_id,
            actor_user_id=user.id,
            reason="PATIENT_REVOKE",
        )
        db.commit()
        db.refresh(card)
    except (ContinuityError, PortalError) as err:
        db.rollback()
        raise _http(err) from err
    return _meta(card)


@public_router.post("/verify", response_model=ContinuityVerifyResponse)
def public_verify(
    payload: ContinuityVerifyRequest,
    db: Session = Depends(get_db),
) -> ContinuityVerifyResponse:
    try:
        data = verify_token(db, raw_token=payload.token, actor_user_id=None, mode="PUBLIC")
        db.commit()
    except ContinuityError as err:
        db.rollback()
        raise _http(err) from err
    return ContinuityVerifyResponse(
        card_id=data["card_id"],
        token_prefix=data["token_prefix"],
        expires_at=data["expires_at"],
        verify_count=data["verify_count"],
        mode=data["mode"],
        snapshot=ContinuitySnapshot(**data["snapshot"]),
    )


@public_router.get("/verify/{token}", response_model=ContinuityVerifyResponse)
def public_verify_get(
    token: str,
    db: Session = Depends(get_db),
) -> ContinuityVerifyResponse:
    try:
        data = verify_token(db, raw_token=token, actor_user_id=None, mode="PUBLIC")
        db.commit()
    except ContinuityError as err:
        db.rollback()
        raise _http(err) from err
    return ContinuityVerifyResponse(
        card_id=data["card_id"],
        token_prefix=data["token_prefix"],
        expires_at=data["expires_at"],
        verify_count=data["verify_count"],
        mode=data["mode"],
        snapshot=ContinuitySnapshot(**data["snapshot"]),
    )


@facility_router.post("/scan", response_model=ContinuityVerifyResponse)
def facility_scan(
    payload: ContinuityVerifyRequest,
    db: Session = Depends(get_db),
    facility_id: UUID = Depends(get_facility_context),
    user: User = Depends(require_permission("patients:read")),
) -> ContinuityVerifyResponse:
    _ = facility_id
    try:
        data = verify_token(
            db, raw_token=payload.token, actor_user_id=user.id, mode="FACILITY"
        )
        db.commit()
    except ContinuityError as err:
        db.rollback()
        raise _http(err) from err
    return ContinuityVerifyResponse(
        card_id=data["card_id"],
        token_prefix=data["token_prefix"],
        expires_at=data["expires_at"],
        verify_count=data["verify_count"],
        mode=data["mode"],
        snapshot=ContinuitySnapshot(**data["snapshot"]),
    )
