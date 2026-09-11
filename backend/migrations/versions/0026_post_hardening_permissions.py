"""seed post-hardening permissions

Revision ID: 0026_post_hardening_permissions
Revises: 0025_notifications
"""

from uuid import uuid4

from alembic import op
import sqlalchemy as sa

revision = "0026_post_hardening_permissions"
down_revision = "0025_notifications"
branch_labels = None
depends_on = None

# (code, description, roles that receive it)
DEFINITIONS: list[tuple[str, str, set[str]]] = [
    ("staff.create", "Create facility staff memberships", {"Hospital Administrator", "System Administrator"}),
    ("staff.read", "List and view facility staff", {"Hospital Administrator", "System Administrator", "Doctor", "Nurse", "Reception"}),
    ("staff.manage", "Activate or deactivate staff", {"Hospital Administrator", "System Administrator"}),
    ("staff.roles.assign", "Assign and remove staff roles", {"Hospital Administrator", "System Administrator"}),
    ("rbac.roles.write", "Create roles", {"System Administrator"}),
    ("rbac.permissions.write", "Create permissions", {"System Administrator"}),
    ("lab.order.create", "Create laboratory orders", {"Doctor", "Nurse", "Hospital Administrator", "System Administrator"}),
    ("lab.sample.collect", "Collect laboratory samples", {"Lab Technician", "Nurse", "Hospital Administrator", "System Administrator"}),
    ("lab.sample.receive", "Receive laboratory samples", {"Lab Technician", "Hospital Administrator", "System Administrator"}),
    ("lab.result.write", "Enter laboratory results", {"Lab Technician", "Hospital Administrator", "System Administrator"}),
    ("lab.result.verify", "Verify laboratory results", {"Lab Technician", "Doctor", "Hospital Administrator", "System Administrator"}),
    ("facilities.create", "Register facilities", {"System Administrator"}),
    ("facilities.read", "View facility profiles", {"Hospital Administrator", "System Administrator", "Reception", "Doctor", "Nurse"}),
    ("facilities.manage", "Update facility profile and status", {"Hospital Administrator", "System Administrator"}),
    ("facilities.department.read", "List facility departments", {"Hospital Administrator", "System Administrator", "Reception", "Doctor", "Nurse"}),
    ("facilities.department.write", "Create and manage departments", {"Hospital Administrator", "System Administrator"}),
    ("clinical.record.read", "View clinical timeline and encounter clinical summary", {"Doctor", "Nurse", "Hospital Administrator", "System Administrator"}),
    ("clinical.vitals.write", "Record patient vitals", {"Nurse", "Doctor", "Hospital Administrator", "System Administrator"}),
    ("clinical.consultation.write", "Create or update consultations", {"Doctor", "Hospital Administrator", "System Administrator"}),
    ("clinical.diagnosis.write", "Record diagnoses", {"Doctor", "Hospital Administrator", "System Administrator"}),
    ("encounters.create", "Open patient encounters", {"Reception", "Doctor", "Nurse", "Hospital Administrator", "System Administrator"}),
    ("encounters.read", "View encounter records", {"Reception", "Doctor", "Nurse", "Lab Technician", "Pharmacist", "Cashier", "Hospital Administrator", "System Administrator"}),
    ("encounters.close", "Close patient encounters", {"Doctor", "Hospital Administrator", "System Administrator"}),
    ("appointments.read", "List appointments", {"Reception", "Doctor", "Nurse", "Hospital Administrator", "System Administrator"}),
    ("appointments.write", "Create appointments and queues", {"Reception", "Hospital Administrator", "System Administrator"}),
    ("coverage.write", "Register patient coverage", {"Reception", "Finance", "Hospital Administrator", "System Administrator"}),
    ("coverage.read", "View patient coverage at facility", {"Reception", "Finance", "Doctor", "Cashier", "Hospital Administrator", "System Administrator"}),
    ("referrals.read", "List and view referrals and transfers", {"Doctor", "Reception", "Hospital Administrator", "System Administrator"}),
]


def upgrade() -> None:
    bind = op.get_bind()
    permissions = sa.table("permissions", sa.column("id"), sa.column("code"), sa.column("description"))
    roles = sa.table("roles", sa.column("id"), sa.column("name"))
    role_permissions = sa.table("role_permissions", sa.column("role_id"), sa.column("permission_id"))

    for code, description, role_names in DEFINITIONS:
        permission_id = bind.execute(sa.select(permissions.c.id).where(permissions.c.code == code)).scalar()
        if permission_id is None:
            permission_id = uuid4()
            bind.execute(sa.insert(permissions).values(id=permission_id, code=code, description=description))

        for role_name in role_names:
            role_id = bind.execute(sa.select(roles.c.id).where(roles.c.name == role_name)).scalar()
            if role_id is None:
                continue
            exists = bind.execute(
                sa.select(role_permissions.c.role_id).where(
                    role_permissions.c.role_id == role_id,
                    role_permissions.c.permission_id == permission_id,
                )
            ).first()
            if exists is None:
                bind.execute(sa.insert(role_permissions).values(role_id=role_id, permission_id=permission_id))


def downgrade() -> None:
    bind = op.get_bind()
    permissions = sa.table("permissions", sa.column("id"), sa.column("code"))
    role_permissions = sa.table("role_permissions", sa.column("permission_id"))
    codes = [code for code, _, _ in DEFINITIONS]
    rows = bind.execute(sa.select(permissions.c.id).where(permissions.c.code.in_(codes))).fetchall()
    for row in rows:
        bind.execute(sa.delete(role_permissions).where(role_permissions.c.permission_id == row.id))
        bind.execute(sa.delete(permissions).where(permissions.c.id == row.id))
