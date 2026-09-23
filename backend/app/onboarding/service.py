"""Facility onboarding kit + migration readiness checklist."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.facilities.models import Facility
from app.pharmacy.models import InventoryItem, Medication
from app.rbac.models import Staff, User
from app.workforce.models import ProfessionalCredential


def facility_onboarding_kit(db: Session, *, facility_id: UUID) -> dict:
    fac = db.get(Facility, facility_id)
    if fac is None:
        raise ValueError("FACILITY_NOT_FOUND")

    staff_count = db.scalar(
        select(func.count()).select_from(Staff).where(
            Staff.facility_id == facility_id, Staff.status == "ACTIVE"
        )
    ) or 0
    users_linked = db.scalar(
        select(func.count()).select_from(User).where(
            User.facility_id == facility_id, User.status == "ACTIVE"
        )
    ) or 0
    # User may not have facility_id — count staff with user_id if present
    try:
        users_linked = db.scalar(
            select(func.count()).select_from(Staff).where(
                Staff.facility_id == facility_id,
                Staff.status == "ACTIVE",
                Staff.user_id.isnot(None),
            )
        ) or 0
    except Exception:
        users_linked = 0

    creds = db.scalar(
        select(func.count()).select_from(ProfessionalCredential).where(
            ProfessionalCredential.facility_id == facility_id,
            ProfessionalCredential.status == "ACTIVE",
        )
    ) or 0

    inv = db.scalar(
        select(func.count()).select_from(InventoryItem).where(
            InventoryItem.facility_id == facility_id,
            InventoryItem.status == "ACTIVE",
        )
    ) or 0

    meds = db.scalar(select(func.count()).select_from(Medication).where(Medication.status == "ACTIVE")) or 0

    steps = [
        {
            "code": "FACILITY_ACTIVE",
            "label": "Facility record ACTIVE",
            "done": str(getattr(fac, "status", "")).upper() == "ACTIVE",
            "value": getattr(fac, "status", None),
        },
        {
            "code": "STAFF_ONBOARDED",
            "label": "At least one active staff member",
            "done": staff_count >= 1,
            "value": int(staff_count),
        },
        {
            "code": "STAFF_LOGIN_LINKED",
            "label": "Staff linked to login accounts",
            "done": users_linked >= 1,
            "value": int(users_linked),
        },
        {
            "code": "CREDENTIALS_LOADED",
            "label": "Professional credentials on file",
            "done": creds >= 1,
            "value": int(creds),
        },
        {
            "code": "INVENTORY_SEEDED",
            "label": "Inventory SKUs registered",
            "done": inv >= 1,
            "value": int(inv),
        },
        {
            "code": "FORMULARY_AVAILABLE",
            "label": "National/local formulary medications present",
            "done": meds >= 1,
            "value": int(meds),
        },
    ]

    done = sum(1 for s in steps if s["done"])
    pct = round(100.0 * done / len(steps), 1)
    band = "GREEN" if pct >= 80 else ("AMBER" if pct >= 50 else "RED")

    return {
        "facility_id": str(facility_id),
        "facility_name": getattr(fac, "name", None),
        "county": getattr(fac, "county", None),
        "completion_pct": pct,
        "band": band,
        "steps": steps,
        "runbook": [
            "1. Confirm facility ACTIVE in registry",
            "2. Create staff + link User accounts with roles",
            "3. Register professional credentials (licence numbers)",
            "4. Seed inventory / minimum stock levels",
            "5. Train on claims preflight + telemedicine + ambulance boards",
            "6. Run reliability readiness-matrix before go-live",
        ],
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "developer": "BAHATI GAD WANGWE",
    }


def migration_playbook() -> dict:
    return {
        "title": "AfyaSync facility migration playbook",
        "phases": [
            {
                "name": "PREPARE",
                "items": [
                    "Export legacy patient index (CSV) with national ID / SHA ID",
                    "Map departments to AfyaSync service codes",
                    "Freeze new registrations on legacy system for cutover window",
                ],
            },
            {
                "name": "LOAD",
                "items": [
                    "Create facility if missing",
                    "Import staff + roles",
                    "Import open appointments / inpatients only (not full history dump on day-1)",
                    "Validate with facility onboarding kit endpoint",
                ],
            },
            {
                "name": "VERIFY",
                "items": [
                    "Patient login with Afya ID",
                    "Book appointment end-to-end",
                    "Submit one claims preflight",
                    "Run fraud-integrity facility-scan (expect clean or explained signals)",
                    "Run reliability readiness-matrix",
                ],
            },
            {
                "name": "GO_LIVE",
                "items": [
                    "Enable SHA_DHA_MODE when tokens available",
                    "Keep offline outbox enabled",
                    "Monitor security-ops access-review for 7 days",
                ],
            },
        ],
        "note": "Playbook is operational guidance — data import scripts remain facility-specific",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "developer": "BAHATI GAD WANGWE",
    }
