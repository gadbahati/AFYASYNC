"""add facility reporting permission

Revision ID: 0028_reports_permission
Revises: 0027_merge_migration_heads
"""

from uuid import uuid4

from alembic import op
import sqlalchemy as sa

revision = "0028_reports_permission"
down_revision = "0027_merge_migration_heads"
branch_labels = None
depends_on = None

PERMISSION = ("reports.read", "View facility operational and financial reports")
ROLES = {"Finance", "Hospital Administrator", "System Administrator"}


def upgrade() -> None:
    bind = op.get_bind()
    permissions = sa.table("permissions", sa.column("id"), sa.column("code"), sa.column("description"))
    roles = sa.table("roles", sa.column("id"), sa.column("name"))
    role_permissions = sa.table("role_permissions", sa.column("role_id"), sa.column("permission_id"))

    permission_id = bind.execute(sa.select(permissions.c.id).where(permissions.c.code == PERMISSION[0])).scalar()
    if permission_id is None:
        permission_id = uuid4()
        bind.execute(sa.insert(permissions).values(id=permission_id, code=PERMISSION[0], description=PERMISSION[1]))

    for role_name in ROLES:
        role_id = bind.execute(sa.select(roles.c.id).where(roles.c.name == role_name)).scalar()
        if role_id is None:
            continue
        exists = bind.execute(
            sa.select(role_permissions.c.role_id).where(
                role_permissions.c.role_id == role_id,
                role_permissions.c.permission_id == permission_id,
            )
        ).first()
        if exists is None:
            bind.execute(sa.insert(role_permissions).values(role_id=role_id, permission_id=permission_id))


def downgrade() -> None:
    bind = op.get_bind()
    permissions = sa.table("permissions", sa.column("id"), sa.column("code"))
    role_permissions = sa.table("role_permissions", sa.column("permission_id"))
    permission_id = bind.execute(sa.select(permissions.c.id).where(permissions.c.code == PERMISSION[0])).scalar()
    if permission_id is not None:
        bind.execute(sa.delete(role_permissions).where(role_permissions.c.permission_id == permission_id))
        bind.execute(sa.delete(permissions).where(permissions.c.id == permission_id))
