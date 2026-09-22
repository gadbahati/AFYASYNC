"""Workforce licensing & credential APIs."""

from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth.dependencies import get_facility_context, require_permission
from app.database import get_db
from app.rbac.models import User
from app.workforce.service import (
    WorkforceError,
    check_staff_credentials,
    facility_compliance,
    register_credential,
)

router = APIRouter(prefix="/api/v1/workforce", tags=["Workforce"])


class CredentialCreate(BaseModel):
    staff_id: UUID
    council_code: str = Field(min_length=2, max_length=40)
    cadre: str = Field(min_length=2, max_length=80)
    licence_number: str = Field(min_length=2, max_length=80)
    issued_on: date | None = None
    expiry_date: date | None = None
    notes: str | None = Field(default=None, max_length=500)


@router.post("/credentials")
def create_credential(
    body: CredentialCreate,
    db: Session = Depends(get_db),
    facility_id: UUID = Depends(get_facility_context),
    user: User = Depends(require_permission("reports.read")),
):
    try:
        cred = register_credential(
            db,
            facility_id=facility_id,
            staff_id=body.staff_id,
            council_code=body.council_code,
            cadre=body.cadre,
            licence_number=body.licence_number,
            issued_on=body.issued_on,
            expiry_date=body.expiry_date,
            notes=body.notes,
            actor_user_id=user.id,
        )
        db.commit()
        return {
            "id": str(cred.id),
            "status": cred.status,
            "licence_number": cred.licence_number,
            "council_code": cred.council_code,
        }
    except WorkforceError as exc:
        code = str(exc)
        status = 404 if "NOT_FOUND" in code else 400
        raise HTTPException(status_code=status, detail=code) from exc


@router.get("/staff/{staff_id}/check")
def staff_check(
    staff_id: UUID,
    db: Session = Depends(get_db),
    facility_id: UUID = Depends(get_facility_context),
    user: User = Depends(require_permission("reports.read")),
):
    _ = user
    try:
        result = check_staff_credentials(db, facility_id=facility_id, staff_id=staff_id)
        db.commit()
        return result
    except WorkforceError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/compliance")
def compliance(
    db: Session = Depends(get_db),
    facility_id: UUID = Depends(get_facility_context),
    user: User = Depends(require_permission("reports.read")),
    days_ahead: int = Query(default=60, ge=1, le=365),
):
    _ = user
    return facility_compliance(db, facility_id=facility_id, days_ahead=days_ahead)
