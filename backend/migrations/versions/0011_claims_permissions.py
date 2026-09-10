"""seed claims permissions

Revision ID: 0011
Revises: 0010
"""

import uuid

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import insert

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

    for code, description in PERMISSIONS:
        stmt = insert(permissions).values(id=uuid.uuid4(), code=code, description=description).on_conflict_do_nothing(index_elements=["code"])
        bind.execute(stmt)

    finance_roles = bind.execute(sa.select(roles.c.id).where(roles.c.name.in_(["Finance", "Hospital Administrator"]))).fetchall()
    for (role_id,) in finance_roles:
        for code, _ in PERMISSIONS:
            permission_id = bind.execute(sa.select(permissions.c.id).where(permissions.c.code == code)).scalar_one()
            stmt = insert(role_permissions).values(role_id=role_id, permission_id=permission_id).on_conflict_do_nothing(index_elements=["role_id", "permission_id"])
            bind.execute(stmt)


def downgrade() -> None:
    bind = op.get_bind()
    permissions = sa.table("permissions", sa.column("id"), sa.column("code"))
    role_permissions = sa.table("role_permissions", sa.column("permission_id"))
    ids = [row[0] for row in bind.execute(sa.select(permissions.c.id).where(permissions.c.code.in_([p[0] for p in PERMISSIONS]))).fetchall()]
    if ids:
        bind.execute(sa.delete(role_permissions).where(role_permissions.c.permission_id.in_(ids)))
        bind.execute(sa.delete(permissions).where(permissions.c.id.in_(ids)))
