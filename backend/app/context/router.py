from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user, get_facility_context
from app.database import get_db
from app.rbac.models import User, Staff, StaffRole, Role, RolePermission, Permission

router = APIRouter(prefix="/api/v1/context", tags=["context"])

@router.get("")
def context_overview(
    user: User = Depends(get_current_user),
    facility_id = Depends(get_facility_context),
    db: Session = Depends(get_db),
):
    from app.auth.dependencies import _is_system_administrator
    is_admin = _is_system_administrator(db, user)
    roles = db.scalars(select(Role.name).join(StaffRole, StaffRole.role_id == Role.id).join(Staff, Staff.id == StaffRole.staff_id).where(Staff.person_id == user.person_id, Staff.status == "ACTIVE").distinct()).all()
    permission_rows = db.execute(select(Permission.code).join(RolePermission, RolePermission.permission_id == Permission.id).join(StaffRole, StaffRole.role_id == Role.id).join(Staff, Staff.id == StaffRole.staff_id).where(Staff.person_id == user.person_id, Staff.status == "ACTIVE").distinct()).all()
    permissions = sorted({row[0] for row in permission_rows})
    scopes = ["facility"]
    prefixes = {
        "operations": ("appointments.", "encounters.", "clinical.", "laboratory.", "pharmacy.", "billing.", "reports."),
        "people": ("patients.", "staff.", "referrals.", "care.", "portal.", "messages."),
        "connect": ("interoperability.", "hie.", "identity.", "referral.", "integrations."),
        "finance": ("claims.", "billing.", "coverage.", "payer.", "revenue.", "settlement.", "contract."),
        "public-health": ("national.", "public_health.", "analytics.", "reports."),
        "compliance": ("security.", "privacy.", "certification.", "risk.", "change.", "production."),
        "resilience": ("offline.", "continuity.", "disaster.", "observability.", "performance.", "integrations."),
        "intelligence": ("analytics.", "insight.", "warehouse.", "revenue.", "coverage."),
    }
    allowed_workspaces = ["operations"] if permissions else []
    if is_admin:
        allowed_workspaces = list(prefixes)
    else:
        for workspace, workspace_prefixes in prefixes.items():
            if any(code.startswith(workspace_prefixes) for code in permissions):
                allowed_workspaces.append(workspace)
    allowed_workspaces = sorted(set(allowed_workspaces))
    if is_admin:
        scopes = ["facility", "network", "county", "national"]
    return {
        "current": {"scope": "facility", "facility_id": str(facility_id)},
        "available_scopes": scopes,
        "roles": list(roles),
        "permissions": permissions,
        "allowed_workspaces": allowed_workspaces,
        "authorization": {"facility_context_required_for_operational_modules": True, "system_administrator": is_admin},
        "context_model": {
            "facility": "Operational scope for one authorized facility.",
            "network": "Aggregated scope for an authorized provider network.",
            "county": "County health-management scope when explicitly authorized.",
            "national": "National scope reserved for explicitly authorized platform/government operations.",
        },
    }
