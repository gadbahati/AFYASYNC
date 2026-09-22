"""Workforce credential registration and compliance scanning."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit.service import record_audit
from app.rbac.models import Staff
from app.workforce.models import ProfessionalCredential

ALLOWED_COUNCILS = {"KMPDC", "NCK", "PPB", "COC", "OTHER"}
ALLOWED_STATUSES = {"ACTIVE", "EXPIRED", "SUSPENDED", "REVOKED", "PENDING_VERIFICATION"}


class WorkforceError(ValueError):
    pass


def _refresh_status(cred: ProfessionalCredential, today: date | None = None) -> None:
    today = today or date.today()
    if cred.status in {"SUSPENDED", "REVOKED"}:
        return
    if cred.expiry_date and cred.expiry_date < today:
        cred.status = "EXPIRED"


def register_credential(
    db: Session,
    *,
    facility_id: UUID,
    staff_id: UUID,
    council_code: str,
    cadre: str,
    licence_number: str,
    issued_on: date | None = None,
    expiry_date: date | None = None,
    notes: str | None = None,
    actor_user_id: UUID | None = None,
) -> ProfessionalCredential:
    staff = db.get(Staff, staff_id)
    if staff is None or staff.facility_id != facility_id:
        raise WorkforceError("STAFF_NOT_FOUND")

    council = council_code.strip().upper()
    if council not in ALLOWED_COUNCILS:
        raise WorkforceError("INVALID_COUNCIL")
    number = licence_number.strip().upper()
    if not number:
        raise WorkforceError("LICENCE_NUMBER_REQUIRED")
    cadre_v = cadre.strip()[:80]
    if not cadre_v:
        raise WorkforceError("CADRE_REQUIRED")

    existing = db.scalar(
        select(ProfessionalCredential).where(
            ProfessionalCredential.staff_id == staff_id,
            ProfessionalCredential.council_code == council,
            ProfessionalCredential.licence_number == number,
        )
    )
    if existing:
        existing.cadre = cadre_v
        existing.issued_on = issued_on
        existing.expiry_date = expiry_date
        existing.notes = notes
        existing.status = "ACTIVE"
        _refresh_status(existing)
        cred = existing
    else:
        cred = ProfessionalCredential(
            staff_id=staff_id,
            facility_id=facility_id,
            council_code=council,
            cadre=cadre_v,
            licence_number=number,
            issued_on=issued_on,
            expiry_date=expiry_date,
            notes=notes,
            status="ACTIVE",
        )
        _refresh_status(cred)
        db.add(cred)

    db.flush()
    record_audit(
        db,
        action="WORKFORCE_CREDENTIAL_REGISTER",
        resource_type="PROFESSIONAL_CREDENTIAL",
        resource_id=str(cred.id),
        result=cred.status,
        user_id=actor_user_id,
        facility_id=facility_id,
        metadata={"council": council, "cadre": cadre_v},
        commit=False,
    )
    return cred


def check_staff_credentials(db: Session, *, facility_id: UUID, staff_id: UUID) -> dict:
    staff = db.get(Staff, staff_id)
    if staff is None or staff.facility_id != facility_id:
        raise WorkforceError("STAFF_NOT_FOUND")

    creds = list(
        db.scalars(
            select(ProfessionalCredential).where(
                ProfessionalCredential.staff_id == staff_id,
                ProfessionalCredential.facility_id == facility_id,
            )
        )
    )
    today = date.today()
    for c in creds:
        _refresh_status(c, today)

    active = [c for c in creds if c.status == "ACTIVE"]
    expired = [c for c in creds if c.status == "EXPIRED"]
    blocked = [c for c in creds if c.status in {"SUSPENDED", "REVOKED"}]

    if blocked:
        decision = "BLOCK"
    elif not creds:
        decision = "MISSING"
    elif expired and not active:
        decision = "EXPIRED"
    elif expired:
        decision = "WARN"
    else:
        decision = "CLEAR"

    return {
        "staff_id": str(staff_id),
        "employee_number": staff.employee_number,
        "decision": decision,
        "credential_count": len(creds),
        "active": len(active),
        "expired": len(expired),
        "blocked": len(blocked),
        "credentials": [
            {
                "id": str(c.id),
                "council_code": c.council_code,
                "cadre": c.cadre,
                "licence_number": c.licence_number,
                "status": c.status,
                "expiry_date": c.expiry_date.isoformat() if c.expiry_date else None,
            }
            for c in creds
        ],
        "developer": "BAHATI GAD WANGWE",
    }


def facility_compliance(db: Session, *, facility_id: UUID, days_ahead: int = 60) -> dict:
    days_ahead = max(1, min(days_ahead, 365))
    today = date.today()
    horizon = today + timedelta(days=days_ahead)

    staff_rows = list(
        db.scalars(
            select(Staff).where(Staff.facility_id == facility_id, Staff.status == "ACTIVE")
        )
    )
    creds = list(
        db.scalars(
            select(ProfessionalCredential).where(ProfessionalCredential.facility_id == facility_id)
        )
    )
    for c in creds:
        _refresh_status(c, today)

    by_staff: dict[UUID, list] = {}
    for c in creds:
        by_staff.setdefault(c.staff_id, []).append(c)

    missing = []
    expiring = []
    expired = []
    for s in staff_rows:
        sc = by_staff.get(s.id, [])
        if not sc:
            missing.append({"staff_id": str(s.id), "employee_number": s.employee_number})
            continue
        for c in sc:
            if c.status == "EXPIRED":
                expired.append(
                    {
                        "staff_id": str(s.id),
                        "employee_number": s.employee_number,
                        "licence_number": c.licence_number,
                        "council_code": c.council_code,
                        "expiry_date": c.expiry_date.isoformat() if c.expiry_date else None,
                    }
                )
            elif c.expiry_date and today <= c.expiry_date <= horizon and c.status == "ACTIVE":
                expiring.append(
                    {
                        "staff_id": str(s.id),
                        "employee_number": s.employee_number,
                        "licence_number": c.licence_number,
                        "council_code": c.council_code,
                        "expiry_date": c.expiry_date.isoformat(),
                    }
                )

    return {
        "facility_id": str(facility_id),
        "active_staff": len(staff_rows),
        "credentials_on_file": len(creds),
        "staff_without_credential": len(missing),
        "expired_count": len(expired),
        "expiring_within_days": days_ahead,
        "expiring_count": len(expiring),
        "missing": missing[:50],
        "expired": expired[:50],
        "expiring": expiring[:50],
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "developer": "BAHATI GAD WANGWE",
    }
