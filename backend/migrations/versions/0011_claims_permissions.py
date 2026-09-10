"""seed claims permissions

Revision ID: 0011
Revises: 0010
"""

from alembic import op
import sqlalchemy as sa

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None

PERMISSIONS = (
    ("claims.create", "Create payer claims"),
    ("claims.validate", "Validate payer claims"),
    ("claims.submit", "Submit payer claims"),
    ("claims.reconcile", "Reconcile payer payments"),
)


def upgrade() -> None:
    bind = op.get_bind()
    permissions = sa.table("permissions", sa.column("id"), sa.column("code"), sa.column("description"))
    roles = sa.table("roles", sa.column("id"), sa.column("name"))
    role_permissions = sa.table("role_permissions", sa.column("role_id"), sa.column("permission_id"))
    import uuid
    for code, description in PERMISSIONS:
        permission_id = uuid.uuid4()
        bind.execute(sa.insert(permissions).values(id=permission_id, code=code, description=description).prefix_with("ON CONFLICT (code) DO NOTHING"))
    finance_roles = bind.execute(sa.select(roles.c.id).where(roles.c.name.in_(["Finance", "Hospital Administrator"]))).fetchall()
    for role in finance_roles:
        for code, _ in PERMISSIONS:
            permission_id = bind.execute(sa.select(permissions.c.id).where(permissions.c.code == code)).scalar_one()
            exists = bind.execute(sa.select(role_permissions.c.role_id).where(role_permissions.c.role_id == role.id, role_permissions.c.permission_id == permission_id)).first()
            if not exists:
                bind.execute(sa.insert(role_permissions).values(role_id=role.id, permission_id=permission_id))


def downgrade() -> None:
    bind = op.get_bind()
    permissions = sa.table("permissions", sa.column("id"), sa.column("code"))
    role_permissions = sa.table("role_permissions", sa.column("permission_id"))
    ids = [r[0] for r in bind.execute(sa.select(permissions.c.id).where(permissions.c.code.in_([p[0] for p in PERMISSIONS]))).fetchall()]
    if ids:
        bind.execute(sa.delete(role_permissions).where(role_permissions.c.permission_id.in_(ids)))
        bind.execute(sa.delete(permissions).where(permissions.c.id.in_(ids)))
