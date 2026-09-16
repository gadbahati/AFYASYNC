"""add clinical care plan permissions

Revision ID: 0066_care_plan_permissions
Revises: 0065_care_plans
"""

from uuid import uuid4
from alembic import op
import sqlalchemy as sa

revision = "0066_care_plan_permissions"
down_revision = "0065_care_plans"
branch_labels = None
depends_on = None

DEFINITIONS = {
    "clinical.care_plan.read": {"Reception", "Nurse", "Doctor", "Clinical Officer", "Hospital Administrator", "System Administrator"},
    "clinical.care_plan.write": {"Nurse", "Doctor", "Clinical Officer", "Hospital Administrator", "System Administrator"},
}


def upgrade() -> None:
    bind = op.get_bind()
    permissions = sa.table("permissions", sa.column("id"), sa.column("code"))
    roles = sa.table("roles", sa.column("id"), sa.column("name"))
    role_permissions = sa.table("role_permissions", sa.column("role_id"), sa.column("permission_id"))
    for code, role_names in DEFINITIONS.items():
        permission_id = bind.execute(sa.select(permissions.c.id).where(permissions.c.code == code)).scalar()
        if permission_id is None:
            permission_id = uuid4()
            bind.execute(sa.insert(permissions).values(id=permission_id, code=code))
        for role_name in role_names:
            role_id = bind.execute(sa.select(roles.c.id).where(roles.c.name == role_name)).scalar()
            if role_id is None:
                continue
            exists = bind.execute(sa.select(role_permissions.c.role_id).where(role_permissions.c.role_id == role_id, role_permissions.c.permission_id == permission_id)).first()
            if exists is None:
                bind.execute(sa.insert(role_permissions).values(role_id=role_id, permission_id=permission_id))


def downgrade() -> None:
    bind = op.get_bind()
    permissions = sa.table("permissions", sa.column("id"), sa.column("code"))
    role_permissions = sa.table("role_permissions", sa.column("permission_id"))
    rows = bind.execute(sa.select(permissions.c.id).where(permissions.c.code.in_(list(DEFINITIONS)))).fetchall()
    for row in rows:
        bind.execute(sa.delete(role_permissions).where(role_permissions.c.permission_id == row.id))
        bind.execute(sa.delete(permissions).where(permissions.c.id == row.id))
