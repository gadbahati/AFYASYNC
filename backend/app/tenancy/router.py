"""Multi-tenant organization control-plane APIs."""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user, get_facility_context
from app.database import get_db
from app.facilities.models import Facility
from app.rbac.models import User
from app.tenancy.models import GovernmentAccess, Organization, OrganizationFacility, OrganizationUser
from app.tenancy.service import (
    accessible_organizations,
    audit,
    get_accessible_organization,
    is_tenant_admin,
    organization_facility_ids,
    require_tenant_admin,
)

router = APIRouter(prefix="/api/v1/tenancy", tags=["tenancy"])


class OrganizationCreate(BaseModel):
    code: str = Field(min_length=2, max_length=120)
    name: str = Field(min_length=2, max_length=220)
    organization_type: str = Field(default="PROVIDER_NETWORK", min_length=2, max_length=40)
    parent_id: UUID | None = None
    description: str | None = None


@router.get("")
def tenancy_overview(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    organizations = accessible_organizations(db, user)
    return {
        "organizations": [
            {
                "id": str(o.id),
                "code": o.code,
                "name": o.name,
                "organization_type": o.organization_type,
                "parent_id": str(o.parent_id) if o.parent_id else None,
                "status": o.status,
                "facility_count": len(organization_facility_ids(db, user=user, organization_id=o.id)),
            }
            for o in organizations
        ],
        "tenant_admin": is_tenant_admin(db, user),
        "system_administrator": any(
            o.code == "PLATFORM:NATIONAL" for o in organizations
        ),
        "model": {
            "organization": "Tenant boundary and hierarchy node.",
            "facility_membership": "Explicit facilities belonging to a tenant.",
            "user_membership": "Explicit users authorized inside a tenant.",
            "isolation": "Operational records remain facility-scoped; tenant membership controls which facilities may be aggregated.",
        },
    }


@router.post("/organizations")
def create_organization(
    payload: OrganizationCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    require_tenant_admin(db, user)
    code = payload.code.strip().upper()
    if db.scalar(select(Organization.id).where(Organization.code == code)):
        raise HTTPException(status_code=409, detail="TENANT_CODE_EXISTS")
    if payload.parent_id:
        parent = get_accessible_organization(db, user=user, organization_id=payload.parent_id)
        _ = parent
    org = Organization(
        code=code,
        name=payload.name.strip(),
        organization_type=payload.organization_type.strip().upper(),
        parent_id=payload.parent_id,
        description=payload.description,
        status=ACTIVE,
    )
    db.add(org)
    db.flush()
    audit(
        db,
        action="TENANT_CREATED",
        user=user,
        organization_id=org.id,
        metadata={"code": org.code, "organization_type": org.organization_type},
    )
    return {
        "id": str(org.id),
        "code": org.code,
        "name": org.name,
        "organization_type": org.organization_type,
        "parent_id": str(org.parent_id) if org.parent_id else None,
        "status": org.status,
    }


@router.post("/organizations/{organization_id}/facilities/{facility_id}")
def add_facility_to_organization(
    organization_id: UUID,
    facility_id: UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    require_tenant_admin(db, user)
    get_accessible_organization(db, user=user, organization_id=organization_id)
    facility = db.scalar(
        select(Facility).where(Facility.id == facility_id, Facility.status == ACTIVE)
    )
    if facility is None:
        raise HTTPException(status_code=404, detail="FACILITY_NOT_FOUND")
    membership = db.get(
        OrganizationFacility,
        {"organization_id": organization_id, "facility_id": facility_id},
    )
    if membership:
        membership.status = ACTIVE
    else:
        db.add(
            OrganizationFacility(
                organization_id=organization_id,
                facility_id=facility_id,
                status=ACTIVE,
            )
        )
    db.flush()
    audit(
        db,
        action="TENANT_FACILITY_ATTACHED",
        user=user,
        organization_id=organization_id,
        metadata={"facility_id": str(facility_id)},
    )
    return {"organization_id": str(organization_id), "facility_id": str(facility_id), "status": ACTIVE}


@router.delete("/organizations/{organization_id}/facilities/{facility_id}")
def remove_facility_from_organization(
    organization_id: UUID,
    facility_id: UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    require_tenant_admin(db, user)
    get_accessible_organization(db, user=user, organization_id=organization_id)
    membership = db.get(
        OrganizationFacility,
        {"organization_id": organization_id, "facility_id": facility_id},
    )
    if membership is None:
        raise HTTPException(status_code=404, detail="TENANT_FACILITY_MEMBERSHIP_NOT_FOUND")
    membership.status = "INACTIVE"
    db.flush()
    audit(
        db,
        action="TENANT_FACILITY_DETACHED",
        user=user,
        organization_id=organization_id,
        metadata={"facility_id": str(facility_id)},
    )
    return {"organization_id": str(organization_id), "facility_id": str(facility_id), "status": "INACTIVE"}


@router.post("/organizations/{organization_id}/users/{target_user_id}")
def add_user_to_organization(
    organization_id: UUID,
    target_user_id: UUID,
    access_level: str = "MEMBER",
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    require_tenant_admin(db, user)
    get_accessible_organization(db, user=user, organization_id=organization_id)
    target = db.get(User, target_user_id)
    if target is None or target.status != ACTIVE:
        raise HTTPException(status_code=404, detail="USER_NOT_FOUND")
    membership = db.get(
        OrganizationUser,
        {"organization_id": organization_id, "user_id": target_user_id},
    )
    level = access_level.strip().upper()[:30] or "MEMBER"
    if membership:
        membership.status = ACTIVE
        membership.access_level = level
    else:
        db.add(
            OrganizationUser(
                organization_id=organization_id,
                user_id=target_user_id,
                access_level=level,
                status=ACTIVE,
            )
        )
    db.flush()
    audit(
        db,
        action="TENANT_USER_ATTACHED",
        user=user,
        organization_id=organization_id,
        metadata={"target_user_id": str(target_user_id), "access_level": level},
    )
    return {"organization_id": str(organization_id), "user_id": str(target_user_id), "access_level": level}


@router.post("/organizations/{organization_id}/government-access/{target_user_id}")
def grant_government_access(
    organization_id: UUID,
    target_user_id: UUID,
    role_code: str = "HEALTH_OFFICER",
    scope_level: str = "COUNTY",
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    require_tenant_admin(db, user)
    org = get_accessible_organization(db, user=user, organization_id=organization_id)
    if org.organization_type not in ("COUNTY_GOVERNMENT", "NATIONAL_GOVERNMENT"):
        raise HTTPException(status_code=400, detail="ORGANIZATION_IS_NOT_GOVERNMENT")
    target = db.get(User, target_user_id)
    if target is None or target.status != ACTIVE:
        raise HTTPException(status_code=404, detail="USER_NOT_FOUND")
    # Government identities are privileged: require MFA enrollment before normal access.
    target.mfa_required = True
    level = scope_level.strip().upper()
    expected = "COUNTY" if org.organization_type == "COUNTY_GOVERNMENT" else "NATIONAL"
    if level != expected:
        raise HTTPException(status_code=400, detail="GOVERNMENT_SCOPE_DOES_NOT_MATCH_ORGANIZATION")
    existing = db.scalar(select(GovernmentAccess).where(GovernmentAccess.organization_id == organization_id, GovernmentAccess.user_id == target_user_id))
    if existing:
        existing.role_code = role_code.strip().upper()[:80] or "HEALTH_OFFICER"
        existing.scope_level = level
        existing.status = ACTIVE
    else:
        db.add(GovernmentAccess(organization_id=organization_id, user_id=target_user_id, role_code=role_code.strip().upper()[:80] or "HEALTH_OFFICER", scope_level=level, status=ACTIVE))
    db.flush()
    audit(db, action="GOVERNMENT_ACCESS_GRANTED", user=user, organization_id=organization_id, metadata={"target_user_id": str(target_user_id), "role_code": role_code, "scope_level": level})
    return {"organization_id": str(organization_id), "user_id": str(target_user_id), "role_code": role_code.strip().upper(), "scope_level": level, "status": ACTIVE}


@router.delete("/organizations/{organization_id}/users/{target_user_id}")
def remove_user_from_organization(
    organization_id: UUID,
    target_user_id: UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    require_tenant_admin(db, user)
    get_accessible_organization(db, user=user, organization_id=organization_id)
    membership = db.get(
        OrganizationUser,
        {"organization_id": organization_id, "user_id": target_user_id},
    )
    if membership is None:
        raise HTTPException(status_code=404, detail="TENANT_USER_MEMBERSHIP_NOT_FOUND")
    membership.status = "INACTIVE"
    db.flush()
    audit(
        db,
        action="TENANT_USER_DETACHED",
        user=user,
        organization_id=organization_id,
        metadata={"target_user_id": str(target_user_id)},
    )
    return {"organization_id": str(organization_id), "user_id": str(target_user_id), "status": "INACTIVE"}


@router.post("/select")
def select_tenant(
    organization_id: UUID,
    user: User = Depends(get_current_user),
    facility_id: UUID = Depends(get_facility_context),
    db: Session = Depends(get_db),
):
    org = get_accessible_organization(db, user=user, organization_id=organization_id)
    facility_ids = organization_facility_ids(db, user=user, organization_id=organization_id)
    if facility_id not in facility_ids and not (
        org.organization_type == "NATIONAL" and is_tenant_admin(db, user)
    ):
        raise HTTPException(
            status_code=403,
            detail="TENANT_CONTEXT_DOES_NOT_INCLUDE_TOKEN_FACILITY",
        )
    audit(
        db,
        action="SELECT_TENANT_CONTEXT",
        user=user,
        organization_id=organization_id,
        metadata={"token_facility_id": str(facility_id), "facility_count": len(facility_ids)},
    )
    return {
        "organization_id": str(org.id),
        "code": org.code,
        "name": org.name,
        "organization_type": org.organization_type,
        "facility_count": len(facility_ids),
        "facility_ids": [str(x) for x in facility_ids[:200]],
        "message": "Tenant context authorized. Requests remain subject to endpoint-level permissions and scope checks.",
    }
