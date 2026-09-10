"""add granular pharmacy permissions

Revision ID: 0017_pharmacy_permissions
Revises: 0016_encounter_sequence
"""

from uuid import uuid4

from alembic import op
import sqlalchemy as sa

revision = "0017_pharmacy_permissions"
down_revision = "0016_encounter_sequence"
branch_labels = None
depends_on = None

PERMISSIONS = (
    ("pharmacy.medication.create", "Create medication catalogue entries"),
    ("pharmacy.prescription.create", "Create patient prescriptions"),
    ("pharmacy.inventory.receive", "Receive medication inventory"),
    ("pharmacy.prescription.dispense", "Dispense patient prescriptions"),
)


def upgrade() -> None:
    bind = op.get_bind()
    permissions = sa.table("permissions", sa.column("id"), sa.column("code"), sa.column("description"))
    roles = sa.table("roles", sa.column("id"), sa.column("name"))
    role_permissions = sa.table("role_permissions", sa.column("role_id"), sa.column("permission_id"))

    for code, description in PERMISSIONS:
        existing = bind.execute(sa.select(permissions.c.id).where(permissions.c.code == code)).scalar()
        if existing is None:
            bind.execute(sa.insert(permissions).values(id=uuid4(), code=code, description=description))

    role_rows = bind.execute(
        sa.select(roles.c.id, roles.c.name).where(
            roles.c.name.in_(["Doctor", "Pharmacist", "Hospital Administrator", "System Administrator"])
        )
    ).fetchall()
    role_map = {
        "Doctor": {"pharmacy.prescription.create"},
        "Pharmacist": {
            "pharmacy.medication.create",
            "pharmacy.inventory.receive",
            "pharmacy.prescription.dispense",
        },
        "Hospital Administrator": {code for code, _ in PERMISSIONS},
        "System Administrator": {code for code, _ in PERMISSIONS},
    }

    for role in role_rows:
        for code in role_map.get(role.name, set()):
            permission_id = bind.execute(sa.select(permissions.c.id).where(permissions.c.code == code)).scalar_one()
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
    ids = [
        row[0]
        for row in bind.execute(
            sa.select(permissions.c.id).where(permissions.c.code.in_([code for code, _ in PERMISSIONS]))
        ).fetchall()
    ]
    if ids:
        bind.execute(sa.delete(role_permissions).where(role_permissions.c.permission_id.in_(ids)))
        bind.execute(sa.delete(permissions).where(permissions.c.id.in_(ids)))
