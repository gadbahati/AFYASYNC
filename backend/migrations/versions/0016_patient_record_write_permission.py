"""add patient record write permission

Revision ID: 0016_patient_record_write_permission
Revises: 0015_patient_facility_scope
"""

from uuid import uuid4

from alembic import op
import sqlalchemy as sa

revision = "0016_patient_record_write_permission"
down_revision = "0015_patient_facility_scope"
branch_labels = None
depends_on = None

PERMISSION_CODE = "patients.record.write"


def upgrade() -> None:
    bind = op.get_bind()
    permissions = sa.table("permissions", sa.column("id"), sa.column("code"), sa.column("description"))
    roles = sa.table("roles", sa.column("id"), sa.column("name"))
    role_permissions = sa.table("role_permissions", sa.column("role_id"), sa.column("permission_id"))
    permission_id = bind.execute(sa.select(permissions.c.id).where(permissions.c.code == PERMISSION_CODE)).scalar()
    if permission_id is None:
        permission_id = uuid4()
        bind.execute(sa.insert(permissions).values(id=permission_id, code=PERMISSION_CODE, description="Update patient demographic records"))
    role_names = {"Reception", "Hospital Administrator", "System Administrator"}
    for role_id, role_name in bind.execute(sa.select(roles.c.id, roles.c.name).where(roles.c.name.in_(role_names))).fetchall():
        exists = bind.execute(sa.select(role_permissions.c.role_id).where(role_permissions.c.role_id == role_id, role_permissions.c.permission_id == permission_id)).first()
        if exists is None:
            bind.execute(sa.insert(role_permissions).values(role_id=role_id, permission_id=permission_id))


def downgrade() -> None:
    bind = op.get_bind()
    permissions = sa.table("permissions", sa.column("id"), sa.column("code"))
    role_permissions = sa.table("role_permissions", sa.column("permission_id"))
    permission_id = bind.execute(sa.select(permissions.c.id).where(permissions.c.code == PERMISSION_CODE)).scalar()
    if permission_id is not None:
        bind.execute(sa.delete(role_permissions).where(role_permissions.c.permission_id == permission_id))
        bind.execute(sa.delete(permissions).where(permissions.c.id == permission_id))
