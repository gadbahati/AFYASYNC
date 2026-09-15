"""Ensure the universal administrator has an explicit facility-scoped RBAC role.

Revision ID: 0058_universal_admin_rbac
Revises: 0057_national_referral_visibility
"""

from uuid import uuid4

from alembic import op
import sqlalchemy as sa

revision = "0058_universal_admin_rbac"
down_revision = "0057_national_referral_visibility"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    roles = sa.table("roles", sa.column("id"), sa.column("name"), sa.column("description"))
    users = sa.table("users", sa.column("id"), sa.column("username"), sa.column("person_id"))
    facilities = sa.table("facilities", sa.column("id"), sa.column("facility_id"))
    staff = sa.table("staff", sa.column("id"), sa.column("person_id"), sa.column("facility_id"), sa.column("status"))
    staff_roles = sa.table("staff_roles", sa.column("staff_id"), sa.column("role_id"), sa.column("facility_id"))
    permissions = sa.table("permissions", sa.column("id"), sa.column("code"))
    role_permissions = sa.table("role_permissions", sa.column("role_id"), sa.column("permission_id"))

    user = bind.execute(
        sa.select(users.c.person_id).where(users.c.username == "afyasync.admin")
    ).scalar()
    facility_id = bind.execute(
        sa.select(facilities.c.id).where(facilities.c.facility_id == "AFYA-DEMO-001")
    ).scalar()
    if user is None or facility_id is None:
        return

    role_id = bind.execute(
        sa.select(roles.c.id).where(roles.c.name == "System Administrator")
    ).scalar()
    if role_id is None:
        role_id = uuid4()
        bind.execute(
            sa.insert(roles).values(
                id=role_id,
                name="System Administrator",
                description="Full AfyaSync platform administration",
            )
        )

    staff_id = bind.execute(
        sa.select(staff.c.id).where(
            staff.c.person_id == user,
            staff.c.facility_id == facility_id,
            staff.c.status == "ACTIVE",
        )
    ).scalar()
    if staff_id is None:
        return

    exists = bind.execute(
        sa.select(staff_roles.c.staff_id).where(
            staff_roles.c.staff_id == staff_id,
            staff_roles.c.role_id == role_id,
            staff_roles.c.facility_id == facility_id,
        )
    ).first()
    if exists is None:
        bind.execute(
            sa.insert(staff_roles).values(
                staff_id=staff_id,
                role_id=role_id,
                facility_id=facility_id,
            )
        )

    for permission_id in bind.execute(sa.select(permissions.c.id)).scalars():
        exists = bind.execute(
            sa.select(role_permissions.c.role_id).where(
                role_permissions.c.role_id == role_id,
                role_permissions.c.permission_id == permission_id,
            )
        ).first()
        if exists is None:
            bind.execute(
                sa.insert(role_permissions).values(
                    role_id=role_id,
                    permission_id=permission_id,
                )
            )


def downgrade() -> None:
    # Keep the administrator account intact; remove only the role assignment
    # and role created by this migration.
    bind = op.get_bind()
    roles = sa.table("roles", sa.column("id"), sa.column("name"))
    role_id = bind.execute(
        sa.select(roles.c.id).where(roles.c.name == "System Administrator")
    ).scalar()
    if role_id is None:
        return
    role_permissions = sa.table("role_permissions", sa.column("role_id"))
    staff_roles = sa.table("staff_roles", sa.column("role_id"))
    bind.execute(sa.delete(role_permissions).where(role_permissions.c.role_id == role_id))
    bind.execute(sa.delete(staff_roles).where(staff_roles.c.role_id == role_id))
    bind.execute(sa.delete(roles).where(roles.c.id == role_id))
