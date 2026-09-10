"""add coverage benefit permission

Revision ID: 0020_coverage_benefit_permission
Revises: 0019_invoice_responsibility
"""

from uuid import uuid4

from alembic import op
import sqlalchemy as sa

revision = "0020_coverage_benefit_permission"
down_revision = "0019_invoice_responsibility"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    permissions = sa.table("permissions", sa.column("id"), sa.column("code"), sa.column("description"))
    roles = sa.table("roles", sa.column("id"), sa.column("name"))
    role_permissions = sa.table("role_permissions", sa.column("role_id"), sa.column("permission_id"))
    code = "coverage.benefit.write"
    permission_id = bind.execute(sa.select(permissions.c.id).where(permissions.c.code == code)).scalar()
    if permission_id is None:
        permission_id = uuid4()
        bind.execute(sa.insert(permissions).values(id=permission_id, code=code, description="Configure payer coverage benefit rules"))

    role_rows = bind.execute(sa.select(roles.c.id, roles.c.name).where(roles.c.name.in_(["Finance", "Hospital Administrator", "System Administrator"]))).fetchall()
    for role in role_rows:
        exists = bind.execute(sa.select(role_permissions.c.role_id).where(role_permissions.c.role_id == role.id, role_permissions.c.permission_id == permission_id)).first()
        if exists is None:
            bind.execute(sa.insert(role_permissions).values(role_id=role.id, permission_id=permission_id))


def downgrade() -> None:
    bind = op.get_bind()
    permissions = sa.table("permissions", sa.column("id"), sa.column("code"))
    role_permissions = sa.table("role_permissions", sa.column("permission_id"))
    permission_id = bind.execute(sa.select(permissions.c.id).where(permissions.c.code == "coverage.benefit.write")).scalar()
    if permission_id is not None:
        bind.execute(sa.delete(role_permissions).where(role_permissions.c.permission_id == permission_id))
        bind.execute(sa.delete(permissions).where(permissions.c.id == permission_id))
