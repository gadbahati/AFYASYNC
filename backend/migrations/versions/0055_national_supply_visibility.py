"""Add explicit national medicine supply visibility permission.

Revision ID: 0055_national_supply_visibility
Revises: 0054_interoperability_access
"""
from uuid import uuid4

from alembic import op
import sqlalchemy as sa

revision = "0055_national_supply_visibility"
down_revision = "0054_interoperability_access"
branch_labels = None
depends_on = None

PERMISSION_CODE = "supply.network.read"
ROLE_NAME = "National Health Supply Administrator"


def upgrade() -> None:
    bind = op.get_bind()
    permissions = sa.table("permissions", sa.column("id"), sa.column("code"), sa.column("description"))
    roles = sa.table("roles", sa.column("id"), sa.column("name"), sa.column("description"))
    role_permissions = sa.table("role_permissions", sa.column("role_id"), sa.column("permission_id"))
    permission_id = bind.execute(sa.select(permissions.c.id).where(permissions.c.code == PERMISSION_CODE)).scalar()
    if permission_id is None:
        permission_id = uuid4()
        bind.execute(sa.insert(permissions).values(id=permission_id, code=PERMISSION_CODE, description="Read aggregated medicine stock and expiry visibility across active facilities"))
    role_id = bind.execute(sa.select(roles.c.id).where(roles.c.name == ROLE_NAME)).scalar()
    if role_id is None:
        role_id = uuid4()
        bind.execute(sa.insert(roles).values(id=role_id, name=ROLE_NAME, description="Explicitly privileged national medicine supply visibility"))
    if bind.execute(sa.select(role_permissions.c.role_id).where(role_permissions.c.role_id == role_id, role_permissions.c.permission_id == permission_id)).first() is None:
        bind.execute(sa.insert(role_permissions).values(role_id=role_id, permission_id=permission_id))


def downgrade() -> None:
    bind = op.get_bind()
    permissions = sa.table("permissions", sa.column("id"), sa.column("code"))
    roles = sa.table("roles", sa.column("id"), sa.column("name"))
    role_permissions = sa.table("role_permissions", sa.column("role_id"), sa.column("permission_id"))
    permission_id = bind.execute(sa.select(permissions.c.id).where(permissions.c.code == PERMISSION_CODE)).scalar()
    role_id = bind.execute(sa.select(roles.c.id).where(roles.c.name == ROLE_NAME)).scalar()
    if role_id is not None and permission_id is not None:
        bind.execute(sa.delete(role_permissions).where(role_permissions.c.role_id == role_id, role_permissions.c.permission_id == permission_id))
    if role_id is not None:
        bind.execute(sa.delete(roles).where(roles.c.id == role_id))
    if permission_id is not None:
        bind.execute(sa.delete(permissions).where(permissions.c.id == permission_id))
