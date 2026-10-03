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

from app.audit.service import record_audit
from app.auth.dependencies import _is_system_administrator
from app.claims.models import Claim
from app.context.module_actions import module_actions_payload
from app.encounters.models import Encounter
from app.facilities.models import Facility
from app.patients.models import PatientFacility
from app.rbac.models import Permission, Role, RolePermission, Staff, StaffRole, User
from app.tenancy.service import organization_facility_ids

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
        if any(
            any(code.startswith(prefix) for prefix in workspace_prefixes)
            for code in permissions
        ):
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
    tenant_id: UUID | None = None,
) -> list[UUID]:
    """Return the facility IDs the caller may read under the given scope."""
    scope = (scope or "facility").strip().lower()
    if scope not in VALID_SCOPES:
        raise HTTPException(status_code=400, detail="INVALID_OPERATING_SCOPE")

    tenant_facilities: list[UUID] | None = None
    if tenant_id is not None:
        tenant_facilities = organization_facility_ids(db, user=user, organization_id=tenant_id)
        if token_facility_id not in tenant_facilities and not _is_system_administrator(db, user):
            raise HTTPException(status_code=403, detail="TENANT_CONTEXT_DOES_NOT_INCLUDE_FACILITY")
        if not tenant_facilities:
            raise HTTPException(status_code=403, detail="TENANT_HAS_NO_ACTIVE_FACILITIES")

    scopes = available_scopes(db, user)
    if scope not in scopes:
        try:
            record_audit(
                db,
                action="SCOPE_NOT_AUTHORIZED",
                resource_type="OPERATING_CONTEXT",
                resource_id=str(token_facility_id),
                result="DENIED",
                user_id=user.id,
                facility_id=token_facility_id,
                metadata={"requested_scope": scope, "available_scopes": scopes},
                commit=True,
            )
        except Exception:
            db.rollback()
        raise HTTPException(
            status_code=403,
            detail={
                "code": "SCOPE_NOT_AUTHORIZED",
                "message": f"Your role cannot use '{scope}' scope. Allowed: {', '.join(scopes)}.",
                "available_scopes": scopes,
            },
        )

    if scope == "facility":
        return [token_facility_id]

    if scope == "network":
        ids = staff_facility_ids(db, user)
        if tenant_facilities is not None:
            ids = [x for x in ids if x in tenant_facilities]
        if token_facility_id not in ids and not _is_system_administrator(db, user):
            raise HTTPException(status_code=403, detail="FACILITY_ACCESS_DENIED")
        if _is_system_administrator(db, user) and not ids:
            return [token_facility_id]
        return ids or [token_facility_id]

    home = db.get(Facility, token_facility_id)
    if home is None:
        raise HTTPException(status_code=403, detail="FACILITY_ACCESS_DENIED")

    if scope == "county":
        county = (home.county or "").strip()
        if not county:
            return [token_facility_id]
        query = select(Facility.id).where(Facility.status == "ACTIVE", Facility.county == county)
        if tenant_facilities is not None:
            query = query.where(Facility.id.in_(tenant_facilities))
        return list(db.scalars(query).all()) or [token_facility_id]

    query = select(Facility.id).where(Facility.status == "ACTIVE")
    if tenant_facilities is not None:
        query = query.where(Facility.id.in_(tenant_facilities))
    return list(db.scalars(query).all()) or [token_facility_id]


def scope_data_summary(
    db: Session,
    *,
    user: User,
    token_facility_id: UUID,
    scope: str,
    tenant_id: UUID | None = None,
) -> dict:
    facility_ids = resolve_facility_ids(
        db, user=user, token_facility_id=token_facility_id, scope=scope, tenant_id=tenant_id
    )

    def _count_facility_col(model) -> int:
        if not facility_ids:
            return 0
        try:
            return int(
                db.scalar(
                    select(func.count()).select_from(model).where(model.facility_id.in_(facility_ids))
                )
                or 0
            )
        except Exception:
            return 0

    patients = 0
    if facility_ids:
        try:
            patients = int(
                db.scalar(
                    select(func.count(func.distinct(PatientFacility.patient_id))).where(
                        PatientFacility.facility_id.in_(facility_ids),
                        PatientFacility.status == "ACTIVE",
                    )
                )
                or 0
            )
        except Exception:
            patients = 0

    facilities = list(
        db.scalars(select(Facility).where(Facility.id.in_(facility_ids)).limit(200)).all()
    )

    return {
        "scope": scope,
        "tenant_id": str(tenant_id) if tenant_id else None,
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
            "patients": patients,
            "encounters": _count_facility_col(Encounter),
            "claims": _count_facility_col(Claim),
        },
        "authorization": {
            "system_administrator": _is_system_administrator(db, user),
            "available_scopes": available_scopes(db, user),
        },
        "note": (
            "Counts reflect facilities authorized under the selected operating scope. "
            "Facility-scoped operational writes still require the token facility context."
        ),
        "developer": "BAHATI GAD WANGWE",
    }


def context_payload(
    db: Session,
    *,
    user: User,
    facility_id: UUID,
    scope: str | None = None,
    tenant_id: UUID | None = None,
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
        db, user=user, token_facility_id=facility_id, scope=active_scope, tenant_id=tenant_id
    )

    return {
        "current": {
            "scope": active_scope,
            "facility_id": str(facility_id),
            "resolved_facility_count": len(resolved),
            "tenant_id": str(tenant_id) if tenant_id else None,
        },
        "available_scopes": scopes,
        "roles": roles,
        "permissions": permissions,
        "allowed_workspaces": allowed_workspaces_for(permissions, is_admin=is_admin),
        "module_actions": module_actions_payload(permissions, is_admin=is_admin),
        "authorization": {
            "facility_context_required_for_operational_modules": True,
            "system_administrator": is_admin,
            "data_scope_enforced": True,
            "module_actions_filtered": True,
        },
        "context_model": {
            "facility": "Operational scope for one authorized facility.",
            "network": "All facilities where this user has ACTIVE staff membership.",
            "county": "ACTIVE facilities in the same county as the token facility (authorized roles only).",
            "national": "All ACTIVE facilities (system administrator only).",
        },
        "developer": "BAHATI GAD WANGWE",
    }


def record_scope_selection(
    db: Session,
    *,
    user: User,
    facility_id: UUID,
    scope: str,
    previous_scope: str | None = None,
) -> dict:
    """Explicit, auditable operating-scope change (Phase 95)."""
    scope = (scope or "facility").strip().lower()
    if scope not in VALID_SCOPES:
        raise HTTPException(status_code=400, detail="INVALID_OPERATING_SCOPE")

    scopes = available_scopes(db, user)
    if scope not in scopes:
        try:
            record_audit(
                db,
                action="SCOPE_CHANGE_DENIED",
                resource_type="OPERATING_CONTEXT",
                resource_id=str(facility_id),
                result="DENIED",
                user_id=user.id,
                facility_id=facility_id,
                metadata={
                    "requested_scope": scope,
                    "previous_scope": previous_scope,
                    "available_scopes": scopes,
                },
                commit=True,
            )
        except Exception:
            db.rollback()
        raise HTTPException(
            status_code=403,
            detail={
                "code": "SCOPE_NOT_AUTHORIZED",
                "message": f"Your role cannot use '{scope}' scope. Allowed: {', '.join(scopes)}.",
                "available_scopes": scopes,
            },
        )

    facility_ids = resolve_facility_ids(
        db, user=user, token_facility_id=facility_id, scope=scope
    )
    try:
        record_audit(
            db,
            action="SET_OPERATING_SCOPE",
            resource_type="OPERATING_CONTEXT",
            resource_id=str(facility_id),
            result="SUCCESS",
            user_id=user.id,
            facility_id=facility_id,
            metadata={
                "scope": scope,
                "previous_scope": previous_scope,
                "resolved_facility_count": len(facility_ids),
            },
            commit=True,
        )
    except Exception:
        db.rollback()

    return {
        "scope": scope,
        "previous_scope": previous_scope,
        "available_scopes": scopes,
        "resolved_facility_count": len(facility_ids),
        "message": f"Operating scope set to {scope}.",
        "developer": "BAHATI GAD WANGWE",
    }
