"""Temporary universal administrator bootstrap.

This command is intended to run as a Railway pre-deploy step, not from the
web application's startup lifecycle. That keeps it single-run and safe when
Uvicorn starts multiple workers.

Credentials are supplied only through environment variables.
"""

from __future__ import annotations

import os

from sqlalchemy import select, text

from app.database import SessionLocal
from app.auth.security import hash_password
from app.facilities.models import Facility
from app.patients.models import Person
from app.rbac.models import Permission, Role, RolePermission, Staff, StaffRole, User
from app.tenancy.models import GovernmentAccess, Organization

USERNAME_DEFAULT = "dev.universal.admin"
FACILITY_CODE = "AFYA-DEV-001"
FACILITY_NAME = "AfyaSync Development Facility"
GOVERNMENT_CODE = "AFYASYNC:DEV-NATIONAL"
GOVERNMENT_NAME = "AfyaSync Development National Authority"
GOVERNMENT_ROLE = "SYSTEM_ADMINISTRATOR"
GOVERNMENT_SCOPE = "NATIONAL"
ADMIN_ROLE = "System Administrator"
LOCK_KEY = 914275631


def seed_dev_universal_admin(*, username: str | None = None, password: str | None = None) -> dict:
    bootstrap_enabled = os.getenv("BOOTSTRAP_DEV_UNIVERSAL_ADMIN_ONCE", "").strip().lower() in {
        "1", "true", "yes",
    }
    if not bootstrap_enabled:
        raise RuntimeError(
            "Development universal administrator bootstrap requires "
            "BOOTSTRAP_DEV_UNIVERSAL_ADMIN_ONCE=true"
        )

    username = (username or os.getenv("DEV_UNIVERSAL_ADMIN_USERNAME") or USERNAME_DEFAULT).strip()
    password = password or os.getenv("DEV_UNIVERSAL_ADMIN_PASSWORD")
    if not password:
        raise ValueError("DEV_UNIVERSAL_ADMIN_PASSWORD is required; no default password exists")
    if len(password) < 16:
        raise ValueError("Development administrator password must be at least 16 characters")

    db = SessionLocal()
    advisory_lock = False
    try:
        # PostgreSQL advisory lock prevents two accidental invocations from
        # racing if the command is ever invoked concurrently.
        if db.get_bind().dialect.name == "postgresql":
            db.execute(text("SELECT pg_advisory_lock(:lock_key)"), {"lock_key": LOCK_KEY})
            advisory_lock = True

        facility = db.scalar(select(Facility).where(Facility.facility_id == FACILITY_CODE))
        if facility is None:
            facility = Facility(
                facility_id=FACILITY_CODE,
                name=FACILITY_NAME,
                facility_type="HOSPITAL",
                county="Kirinyaga",
                status="ACTIVE",
            )
            db.add(facility)
            db.flush()
        else:
            facility.status = "ACTIVE"

        user = db.scalar(select(User).where(User.username == username))
        if user is None:
            person = Person(first_name="AfyaSync", last_name="Development Administrator", status="ACTIVE")
            db.add(person)
            db.flush()
            user = User(
                person_id=person.id,
                username=username,
                password_hash=hash_password(password),
                status="ACTIVE",
            )
            db.add(user)
            db.flush()
            created_user = True
        else:
            created_user = False
            user.status = "ACTIVE"
            user.password_hash = hash_password(password)

        staff = db.scalar(
            select(Staff).where(
                Staff.person_id == user.person_id,
                Staff.facility_id == facility.id,
            )
        )
        if staff is None:
            staff = Staff(
                facility_id=facility.id,
                person_id=user.person_id,
                employee_number="DEV-UNIVERSAL-001",
                status="ACTIVE",
            )
            db.add(staff)
            db.flush()
        else:
            staff.status = "ACTIVE"

        role = db.scalar(select(Role).where(Role.name == ADMIN_ROLE))
        if role is None:
            role = Role(
                name=ADMIN_ROLE,
                description="Full AfyaSync platform administration",
            )
            db.add(role)
            db.flush()

        staff_role = db.scalar(
            select(StaffRole).where(
                StaffRole.staff_id == staff.id,
                StaffRole.role_id == role.id,
                StaffRole.facility_id == facility.id,
            )
        )
        if staff_role is None:
            db.add(
                StaffRole(
                    staff_id=staff.id,
                    role_id=role.id,
                    facility_id=facility.id,
                )
            )

        for permission in db.scalars(select(Permission)).all():
            existing = db.scalar(
                select(RolePermission).where(
                    RolePermission.role_id == role.id,
                    RolePermission.permission_id == permission.id,
                )
            )
            if existing is None:
                db.add(RolePermission(role_id=role.id, permission_id=permission.id))

        government = db.scalar(select(Organization).where(Organization.code == GOVERNMENT_CODE))
        if government is None:
            government = Organization(
                code=GOVERNMENT_CODE,
                name=GOVERNMENT_NAME,
                organization_type="NATIONAL_GOVERNMENT",
                status="ACTIVE",
                description="Temporary AfyaSync development organization. Remove before production handover.",
            )
            db.add(government)
            db.flush()
        else:
            government.status = "ACTIVE"

        gov_access = db.scalar(
            select(GovernmentAccess).where(
                GovernmentAccess.organization_id == government.id,
                GovernmentAccess.user_id == user.id,
            )
        )
        if gov_access is None:
            db.add(
                GovernmentAccess(
                    organization_id=government.id,
                    user_id=user.id,
                    role_code=GOVERNMENT_ROLE,
                    scope_level=GOVERNMENT_SCOPE,
                    status="ACTIVE",
                )
            )
        else:
            gov_access.role_code = GOVERNMENT_ROLE
            gov_access.scope_level = GOVERNMENT_SCOPE
            gov_access.status = "ACTIVE"

        user.mfa_required = True

        db.commit()
        return {
            "username": username,
            "created_user": created_user,
            "facility": FACILITY_NAME,
            "government_organization": GOVERNMENT_NAME,
            "government_scope": GOVERNMENT_SCOPE,
            "government_mfa_required": True,
            "temporary": True,
        }
    except Exception:
        db.rollback()
        raise
    finally:
        if advisory_lock:
            try:
                db.execute(text("SELECT pg_advisory_unlock(:lock_key)"), {"lock_key": LOCK_KEY})
            except Exception:
                pass
        db.close()


if __name__ == "__main__":
    print("DEV_UNIVERSAL_ADMIN_BOOTSTRAP:", seed_dev_universal_admin())
