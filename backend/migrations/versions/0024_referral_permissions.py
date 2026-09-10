"""add referral and transfer permissions

Revision ID: 0024_referral_permissions
Revises: 0023_referrals_transfers
"""

from uuid import uuid4

from alembic import op
import sqlalchemy as sa

revision = "0024_referral_permissions"
down_revision = "0023_referrals_transfers"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    permissions = sa.table("permissions", sa.column("id"), sa.column("code"), sa.column("description"))
    roles = sa.table("roles", sa.column("id"), sa.column("name"))
    role_permissions = sa.table("role_permissions", sa.column("role_id"), sa.column("permission_id"))

    definitions = (
        ("referrals.create", "Create patient referrals"),
        ("referrals.manage", "Manage referral and transfer status"),
        ("referrals.transfer", "Request interfacility patient transfers"),
    )
    ids = {}
    for code, description in definitions:
        permission_id = bind.execute(sa.select(permissions.c.id).where(permissions.c.code == code)).scalar()
        if permission_id is None:
            permission_id = uuid4()
            bind.execute(sa.insert(permissions).values(id=permission_id, code=code, description=description))
        ids[code] = permission_id

    mappings = {
        "Doctor": {"referrals.create", "referrals.transfer"},
        "Hospital Administrator": set(ids),
        "System Administrator": set(ids),
    }
    for role_name, codes in mappings.items():
        role_id = bind.execute(sa.select(roles.c.id).where(roles.c.name == role_name)).scalar()
        if role_id is None:
            continue
        for code in codes:
            exists = bind.execute(sa.select(role_permissions.c.role_id).where(role_permissions.c.role_id == role_id, role_permissions.c.permission_id == ids[code])).first()
            if exists is None:
                bind.execute(sa.insert(role_permissions).values(role_id=role_id, permission_id=ids[code]))


def downgrade() -> None:
    bind = op.get_bind()
    permissions = sa.table("permissions", sa.column("id"), sa.column("code"))
    role_permissions = sa.table("role_permissions", sa.column("permission_id"))
    codes = ["referrals.create", "referrals.manage", "referrals.transfer"]
    rows = bind.execute(sa.select(permissions.c.id).where(permissions.c.code.in_(codes))).fetchall()
    for row in rows:
        bind.execute(sa.delete(role_permissions).where(role_permissions.c.permission_id == row.id))
        bind.execute(sa.delete(permissions).where(permissions.c.id == row.id))
