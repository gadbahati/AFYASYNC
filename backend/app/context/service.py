"""Phase 90 — Operating context data scope.

Navigation authorization (Phase 89) is not enough for a national platform.
Selected operating context must change which facilities' records the API may
aggregate or return.

Scopes
------
facility  — single facility from the access token (staff membership required)
network   — every facility where this person has ACTIVE staff membership
county    — ACTIVE facilities in the same county as the token facility
            (requires county or national scope authorization)
national  — all ACTIVE facilities (requires national scope authorization)

Network/county tenancy tables are intentionally not invented here; resolution
uses existing Staff + Facility records so the behaviour is real, auditable,
and facility-isolated for ordinary staff.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth.dependencies import _is_system_administrator
from app.claims.models import Claim
from app.encounters.models import Encounter
from app.facilities.models import Facility
from app.patients.models import Patient
from app.rbac.models import Permission, Role, RolePermission, Staff, StaffRole, User

VALID_SCOPES = ("facility", "network", "county", "national")


def user_permission_codes(db: Session, user: User) -> list[str]:
    rows = db.execute(
        select(Permission.code)
        .join(RolePermission, RolePermission.permission_id == Permission.id)
        .join(StaffRole, StaffRole.role_id == RolePermission.role_id)
        .join(Staff, Staff.id == StaffRole.staff_id)
        .where(Staff.person_id == user.person_id, Staff.status == "ACTIVE")
        .distinct()
    ).all()
    return sorted({row[0] for row in rows})


def user_role_names(db: Session, user: User) -> list[str]:
    return list(
        db.scalars(
            select(Role.name)
            .join(StaffRole, StaffRole.role_id == Role.id)
            .join(Staff, Staff.id == StaffRole.staff_id)
            .where(Staff.person_id == user.person_id, Staff.status == "ACTIVE")
            .distinct()
        ).all()
    )


def available_scopes(db: Session, user: User) -> list[str]:
    if _is_system_administrator(db, user):
        return ["facility", "network", "county", "national"]
    return ["facility", "network"]


def allowed_workspaces_for(permissions: list[str], *, is_admin: bool) -> list[str]:
    prefixes = {
        "operations": (
            "appointments.",
            "encounters.",
            "clinical.",
            "laboratory.",
            "pharmacy.",
            "billing.",
            "reports.",
        ),
        "people": ("patients.", "staff.", "referrals.", "care.", "portal.", "messages."),
        "connect": ("interoperability.", "hie.", "identity.", "referral.", "integrations."),
        "finance": (
            "claims.",
            "billing.",
            "coverage.",
            "payer.",
            "revenue.",
            "settlement.",
            "contract.",
        ),
        "public-health": ("national.", "public_health.", "analytics.", "reports."),
        "compliance": (
            "security.",
            "privacy.",
            "certification.",
            "risk.",
            "change.",
            "production.",
        ),
        "resilience": (
            "offline.",
            "continuity.",
            "disaster.",
            "observability.",
            "performance.",
            "integrations.",
        ),
        "intelligence": ("analytics.", "insight.", "warehouse.", "revenue.", "coverage."),
    }
    if is_admin:
        return sorted(prefixes.keys())
    allowed = ["operations"] if permissions else []
    for workspace, workspace_prefixes in prefixes.items():
        if any(code.startswith(workspace_prefixes) for code in permissions):
            allowed.append(workspace)
    return sorted(set(allowed))


def staff_facility_ids(db: Session, user: User) -> list[UUID]:
    if user.person_id is None:
        return []
    return list(
        db.scalars(
            select(Staff.facility_id)
            .join(Facility, Facility.id == Staff.facility_id)
            .where(
                Staff.person_id == user.person_id,
                Staff.status == "ACTIVE",
                Facility.status == "ACTIVE",
            )
            .distinct()
        ).all()
    )


def resolve_facility_ids(
    db: Session,
    *,
    user: User,
    token_facility_id: UUID,
    scope: str,
) -> list[UUID]:
    """Return the facility IDs the caller may read under the given scope."""
    scope = (scope or "facility").strip().lower()
    if scope not in VALID_SCOPES:
        raise HTTPException(status_code=400, detail="INVALID_OPERATING_SCOPE")

    scopes = available_scopes(db, user)
    if scope not in scopes:
        raise HTTPException(status_code=403, detail="SCOPE_NOT_AUTHORIZED")

    if scope == "facility":
        # Token facility already validated by get_facility_context.
        return [token_facility_id]

    if scope == "network":
        ids = staff_facility_ids(db, user)
        if token_facility_id not in ids and not _is_system_administrator(db, user):
            raise HTTPException(status_code=403, detail="FACILITY_ACCESS_DENIED")
        if _is_system_administrator(db, user) and not ids:
            # Admin with no staff rows still operates at least on the token facility.
            return [token_facility_id]
        return ids or [token_facility_id]

    home = db.get(Facility, token_facility_id)
    if home is None:
        raise HTTPException(status_code=403, detail="FACILITY_ACCESS_DENIED")

    if scope == "county":
        county = (home.county or "").strip()
        if not county:
            # No county on home facility → cannot expand safely.
            return [token_facility_id]
        return list(
            db.scalars(
                select(Facility.id).where(
                    Facility.status == "ACTIVE",
                    Facility.county == county,
                )
            ).all()
        ) or [token_facility_id]

    # national
    return list(db.scalars(select(Facility.id).where(Facility.status == "ACTIVE")).all()) or [
        token_facility_id
    ]


def scope_data_summary(
    db: Session,
    *,
    user: User,
    token_facility_id: UUID,
    scope: str,
) -> dict:
    facility_ids = resolve_facility_ids(
        db, user=user, token_facility_id=token_facility_id, scope=scope
    )

    def _count(model) -> int:
        if not facility_ids:
            return 0
        col = getattr(model, "facility_id", None)
        if col is None:
            return 0
        try:
            return int(
                db.scalar(select(func.count()).select_from(model).where(col.in_(facility_ids))) or 0
            )
        except Exception:
            return 0

    facilities = list(
        db.scalars(select(Facility).where(Facility.id.in_(facility_ids)).limit(200)).all()
    )

    return {
        "scope": scope,
        "facility_count": len(facility_ids),
        "facility_ids": [str(x) for x in facility_ids[:100]],
        "facilities": [
            {
                "id": str(f.id),
                "name": f.name,
                "county": f.county,
                "status": f.status,
                "facility_code": getattr(f, "facility_id", None),
            }
            for f in facilities[:50]
        ],
        "counts": {
            "patients": _count(Patient),
            "encounters": _count(Encounter),
            "claims": _count(Claim),
        },
        "authorization": {
            "system_administrator": _is_system_administrator(db, user),
            "available_scopes": available_scopes(db, user),
        },
        "note": (
            "Counts reflect facilities authorized under the selected operating scope. "
            "Facility-scoped operational writes still require the token facility context."
        ),
    }


def context_payload(
    db: Session,
    *,
    user: User,
    facility_id: UUID,
    scope: str | None = None,
) -> dict:
    is_admin = _is_system_administrator(db, user)
    permissions = user_permission_codes(db, user)
    roles = user_role_names(db, user)
    scopes = available_scopes(db, user)
    active_scope = (scope or "facility").strip().lower()
    if active_scope not in VALID_SCOPES:
        active_scope = "facility"
    if active_scope not in scopes:
        active_scope = "facility"

    resolved = resolve_facility_ids(
        db, user=user, token_facility_id=facility_id, scope=active_scope
    )

    return {
        "current": {
            "scope": active_scope,
            "facility_id": str(facility_id),
            "resolved_facility_count": len(resolved),
        },
        "available_scopes": scopes,
        "roles": roles,
        "permissions": permissions,
        "allowed_workspaces": allowed_workspaces_for(permissions, is_admin=is_admin),
        "authorization": {
            "facility_context_required_for_operational_modules": True,
            "system_administrator": is_admin,
            "data_scope_enforced": True,
        },
        "context_model": {
            "facility": "Operational scope for one authorized facility.",
            "network": "All facilities where this user has ACTIVE staff membership.",
            "county": "ACTIVE facilities in the same county as the token facility (authorized roles only).",
            "national": "All ACTIVE facilities (system administrator only).",
        },
    }
