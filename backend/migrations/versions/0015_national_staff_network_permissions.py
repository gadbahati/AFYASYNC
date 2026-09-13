"""add national staff network administration permissions

Revision ID: 0015_national_staff_network_permissions
Revises: 0014_national_reporting_permission
"""

from uuid import uuid4

from alembic import op
import sqlalchemy as sa

revision = "0015_national_staff_network_permissions"
down_revision = "0014_national_reporting_permission"
branch_labels = None
depends_on = None

PERMISSIONS = (
    ("staff.network.read", "View aggregated cross-facility staff membership metadata"),
    ("staff.network.manage", "Manage cross-facility staff membership and role assignments"),
)
ROLE_NAME = "National Health Administrator"


def upgrade() -> None:
    bind = op.get_bind()
    permissions = sa.table("permissions", sa.column("id"), sa.column("code"), sa.column("description"))
    roles = sa.table("roles", sa.column("id"), sa.column("name"))
    role_permissions = sa.table("role_permissions", sa.column("role_id"), sa.column("permission_id"))

    role_id = bind.execute(sa.select(roles.c.id).where(roles.c.name == ROLE_NAME)).scalar()
    if role_id is None:
        return

    for code, description in PERMISSIONS:
        permission_id = bind.execute(sa.select(permissions.c.id).where(permissions.c.code == code)).scalar()
        if permission_id is None:
            permission_id = uuid4()
            bind.execute(sa.insert(permissions).values(id=permission_id, code=code, description=description))
        exists = bind.execute(sa.select(role_permissions.c.role_id).where(
            role_permissions.c.role_id == role_id,
            role_permissions.c.permission_id == permission_id,
        )).first()
        if exists is None:
            bind.execute(sa.insert(role_permissions).values(role_id=role_id, permission_id=permission_id))


def downgrade() -> None:
    bind = op.get_bind()
    permissions = sa.table("permissions", sa.column("id"), sa.column("code"))
    roles = sa.table("roles", sa.column("id"), sa.column("name"))
    role_permissions = sa.table("role_permissions", sa.column("role_id"), sa.column("permission_id"))
    role_id = bind.execute(sa.select(roles.c.id).where(roles.c.name == ROLE_NAME)).scalar()
    if role_id is None:
        return
    for code, _ in PERMISSIONS:
        permission_id = bind.execute(sa.select(permissions.c.id).where(permissions.c.code == code)).scalar()
        if permission_id is not None:
            bind.execute(sa.delete(role_permissions).where(
                role_permissions.c.role_id == role_id,
                role_permissions.c.permission_id == permission_id,
            ))
            bind.execute(sa.delete(permissions).where(permissions.c.id == permission_id))
