"""add patient access permissions

Revision ID: 0016_patient_access_permissions
Revises: 0015_identity_sequences
"""

from uuid import uuid4

from alembic import op
import sqlalchemy as sa

revision = "0016_patient_access_permissions"
down_revision = "0015_identity_sequences"
branch_labels = None
depends_on = None

PERMISSIONS = (
    ("patients.search", "Search patient records"),
)
ROLES = ("Reception", "Doctor", "Nurse", "Lab Technician", "Pharmacist", "Cashier", "Finance", "Hospital Administrator", "System Administrator")


def upgrade() -> None:
    bind = op.get_bind()
    permissions = sa.table("permissions", sa.column("id"), sa.column("code"), sa.column("description"))
    roles = sa.table("roles", sa.column("id"), sa.column("name"))
    role_permissions = sa.table("role_permissions", sa.column("role_id"), sa.column("permission_id"))

    permission_ids = {}
    for code, description in PERMISSIONS:
        existing = bind.execute(sa.select(permissions.c.id).where(permissions.c.code == code)).scalar()
        if existing is None:
            existing = uuid4()
            bind.execute(sa.insert(permissions).values(id=existing, code=code, description=description))
        permission_ids[code] = existing

    role_rows = bind.execute(sa.select(roles.c.id).where(roles.c.name.in_(ROLES))).fetchall()
    for role in role_rows:
        for permission_id in permission_ids.values():
            exists = bind.execute(
                sa.select(role_permissions.c.role_id).where(
                    role_permissions.c.role_id == role.id,
                    role_permissions.c.permission_id == permission_id,
                )
            ).first()
            if exists is None:
                bind.execute(sa.insert(role_permissions).values(role_id=role.id, permission_id=permission_id))


def downgrade() -> None:
    bind = op.get_bind()
    permissions = sa.table("permissions", sa.column("id"), sa.column("code"))
    role_permissions = sa.table("role_permissions", sa.column("permission_id"))
    ids = [row[0] for row in bind.execute(sa.select(permissions.c.id).where(permissions.c.code.in_([p[0] for p in PERMISSIONS]))).fetchall()]
    if ids:
        bind.execute(sa.delete(role_permissions).where(role_permissions.c.permission_id.in_(ids)))
        bind.execute(sa.delete(permissions).where(permissions.c.id.in_(ids)))
