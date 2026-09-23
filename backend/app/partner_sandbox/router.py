"""Partner integration sandbox APIs."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth.dependencies import get_facility_context, require_permission
from app.database import get_db
from app.partner_sandbox.contracts import contracts_catalogue
from app.partner_sandbox.service import (
    SandboxError,
    register_interest,
    sandbox_claim_preflight,
    sandbox_eligibility,
    sandbox_hie_echo,
)
from app.rbac.models import User

router = APIRouter(prefix="/api/v1/partner-sandbox", tags=["PartnerSandbox"])


def _map(err: SandboxError) -> HTTPException:
    return HTTPException(status_code=400, detail=str(err))


class EligibilityBody(BaseModel):
    member_id: str | None = Field(default=None, max_length=80)
    national_id: str | None = Field(default=None, max_length=40)


class PreflightBody(BaseModel):
    sample: bool = True


class RegisterBody(BaseModel):
    organisation: str = Field(min_length=2, max_length=200)
    contact_email: str = Field(min_length=5, max_length=200)
    use_case: str = Field(min_length=5, max_length=500)
    contact_phone: str | None = Field(default=None, max_length=40)


class HieBody(BaseModel):
    note: str | None = Field(default=None, max_length=200)


@router.get("/contracts")
def contracts(
    user: User = Depends(require_permission("reports.read")),
):
    _ = user
    return contracts_catalogue()


@router.post("/eligibility")
def eligibility(
    body: EligibilityBody,
    user: User = Depends(require_permission("reports.read")),
):
    _ = user
    try:
        return sandbox_eligibility(member_id=body.member_id, national_id=body.national_id)
    except SandboxError as e:
        raise _map(e) from e


@router.post("/claim-preflight")
def claim_preflight(
    body: PreflightBody,
    user: User = Depends(require_permission("reports.read")),
):
    _ = user
    return sandbox_claim_preflight(sample=body.sample)


@router.post("/hie-echo")
def hie_echo(
    body: HieBody,
    user: User = Depends(require_permission("reports.read")),
):
    _ = user
    return sandbox_hie_echo(note=body.note)


@router.post("/register-interest")
def register(
    body: RegisterBody,
    db: Session = Depends(get_db),
    facility_id: UUID | None = Depends(get_facility_context),
    user: User = Depends(require_permission("reports.read")),
):
    _ = user
    try:
        row = register_interest(
            db,
            organisation=body.organisation,
            contact_email=body.contact_email,
            use_case=body.use_case,
            contact_phone=body.contact_phone,
            facility_id=facility_id,
        )
        db.commit()
        return {
            "registration_id": str(row.id),
            "status": row.status,
            "organisation": row.organisation,
        }
    except SandboxError as e:
        raise _map(e) from e
