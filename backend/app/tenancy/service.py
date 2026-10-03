"""Tenant authorization and control-plane services for Phase 119."""
from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit.service import record_audit
from app.auth.dependencies import _is_system_administrator
from app.facilities.models import Facility
from app.rbac.models import Permission, Role, RolePermission, Staff, StaffRole, User
from app.tenancy.models import Organization, OrganizationFacility, OrganizationUser


ACTIVE = "ACTIVE"


def is_tenant_admin(db: Session, user: User) -> bool:
    if _is_system_administrator(db, user):
        return True
    if user.person_id is None:
        return False
    return db.scalar(
        select(Permission.id)
        .join(RolePermission, RolePermission.permission_id == Permission.id)
        .join(Role, Role.id == RolePermission.role_id)
        .join(StaffRole, StaffRole.role_id == Role.id)
        .join(Staff, Staff.id == StaffRole.staff_id)
        .where(
            Permission.code == "tenancy.admin",
            Staff.person_id == user.person_id,
            Staff.status == ACTIVE,
            StaffRole.facility_id == Staff.facility_id,
        )
        .limit(1)
    ) is not None


def require_tenant_admin(db: Session, user: User) -> User:
    if not is_tenant_admin(db, user):
        raise HTTPException(status_code=403, detail="TENANT_ADMIN_REQUIRED")
    return user


def accessible_organizations(db: Session, user: User) -> list[Organization]:
    if _is_system_administrator(db, user):
        return list(
            db.scalars(
                select(Organization)
                .where(Organization.status == ACTIVE)
                .order_by(Organization.organization_type, Organization.name)
            ).all()
        )
    return list(
        db.scalars(
            select(Organization)
            .join(
                OrganizationUser,
                OrganizationUser.organization_id == Organization.id,
            )
            .where(
                OrganizationUser.user_id == user.id,
                OrganizationUser.status == ACTIVE,
                Organization.status == ACTIVE,
            )
            .order_by(Organization.organization_type, Organization.name)
        ).all()
    )


def get_accessible_organization(
    db: Session, *, user: User, organization_id: UUID
) -> Organization:
    org = db.scalar(
        select(Organization).where(
            Organization.id == organization_id,
            Organization.status == ACTIVE,
        )
    )
    if org is None:
        raise HTTPException(status_code=404, detail="TENANT_NOT_FOUND")
    if _is_system_administrator(db, user):
        return org
    allowed = db.scalar(
        select(OrganizationUser.organization_id).where(
            OrganizationUser.organization_id == organization_id,
            OrganizationUser.user_id == user.id,
            OrganizationUser.status == ACTIVE,
        )
    )
    if allowed is None:
        raise HTTPException(status_code=403, detail="TENANT_ACCESS_DENIED")
    return org


def organization_facility_ids(
    db: Session, *, user: User, organization_id: UUID
) -> list[UUID]:
    get_accessible_organization(db, user=user, organization_id=organization_id)
    return list(
        db.scalars(
            select(OrganizationFacility.facility_id)
            .join(Facility, Facility.id == OrganizationFacility.facility_id)
            .where(
                OrganizationFacility.organization_id == organization_id,
                OrganizationFacility.status == ACTIVE,
                Facility.status == ACTIVE,
            )
        ).all()
    )


def audit(
    db: Session,
    *,
    action: str,
    user: User,
    organization_id: UUID,
    metadata: dict | None = None,
    result: str = "SUCCESS",
) -> None:
    try:
        record_audit(
            db,
            action=action,
            resource_type="ORGANIZATION",
            resource_id=str(organization_id),
            result=result,
            user_id=user.id,
            metadata=metadata or {},
            commit=True,
        )
    except Exception:
        db.rollback()
