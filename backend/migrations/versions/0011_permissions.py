"""seed claims, integration, clinical and queue permissions

Revision ID: 0011
Revises: 0010
"""

from uuid import uuid4

from alembic import op
import sqlalchemy as sa

revision = "0011_permissions"
down_revision = "0010"
branch_labels = None
depends_on = None

PERMISSIONS = (
    ("claims.create", "Create payer claims"),
    ("claims.validate", "Validate payer claims"),
    ("claims.submit", "Submit payer claims"),
    ("claims.reconcile", "Reconcile payer payments"),
    ("integrations.write", "Create and configure integrations"),
    ("integrations.queue", "Queue integration transactions"),
    ("clinical.vitals.write", "Record patient vital signs"),
    ("clinical.consultation.write", "Create and update clinical consultations"),
    ("clinical.diagnosis.write", "Record clinical diagnoses"),
    ("appointments.write", "Create appointments and queues"),
    ("queue.checkin", "Check patients into clinical queues"),
    ("queue.manage", "Manage patient queue status"),
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

    role_names = [
        "Finance",
        "Hospital Administrator",
        "System Administrator",
        "Reception",
        "Doctor",
        "Nurse",
        "Lab Technician",
        "Pharmacist",
    ]
    role_rows = bind.execute(sa.select(roles.c.id, roles.c.name).where(roles.c.name.in_(role_names))).fetchall()
    role_permissions_map = {
        "Reception": {"appointments.write", "queue.checkin", "queue.manage"},
        "Doctor": {"clinical.vitals.write", "clinical.consultation.write", "clinical.diagnosis.write", "queue.manage"},
        "Nurse": {"clinical.vitals.write", "queue.manage"},
        "Finance": {"claims.create", "claims.validate", "claims.submit", "claims.reconcile"},
        "Hospital Administrator": {code for code, _ in PERMISSIONS},
        "System Administrator": {code for code, _ in PERMISSIONS},
    }
    for role in role_rows:
        codes = role_permissions_map.get(role.name, set())
        for code in codes:
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
            sa.select(permissions.c.id).where(permissions.c.code.in_([p[0] for p in PERMISSIONS]))
        ).fetchall()
    ]
    if ids:
        bind.execute(sa.delete(role_permissions).where(role_permissions.c.permission_id.in_(ids)))
        bind.execute(sa.delete(permissions).where(permissions.c.id.in_(ids)))
