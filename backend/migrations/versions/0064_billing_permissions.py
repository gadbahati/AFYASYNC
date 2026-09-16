"""add billing read/write permissions and facility role assignments

Revision ID: 0064_billing_permissions
Revises: 0063_seed_kenya_facility_directory
"""

from uuid import uuid4

from alembic import op
import sqlalchemy as sa

revision = "0064_billing_permissions"
down_revision = "0063_seed_kenya_facility_directory"
branch_labels = None
depends_on = None

DEFINITIONS: list[tuple[str, str, set[str]]] = [
    ("billing.service.read", "View active facility billing services", {"Reception", "Finance", "Cashier", "Hospital Administrator", "System Administrator"}),
    ("billing.service.write", "Create and manage facility billing services", {"Finance", "Cashier", "Hospital Administrator", "System Administrator"}),
    ("billing.charge.write", "Create patient billing charges", {"Reception", "Finance", "Cashier", "Hospital Administrator", "System Administrator"}),
    ("billing.invoice.read", "View facility invoices", {"Reception", "Finance", "Cashier", "Hospital Administrator", "System Administrator"}),
    ("billing.invoice.write", "Create patient invoices", {"Reception", "Finance", "Cashier", "Hospital Administrator", "System Administrator"}),
    ("billing.payment.write", "Record patient payments", {"Reception", "Finance", "Cashier", "Hospital Administrator", "System Administrator"}),
]


def upgrade() -> None:
    bind = op.get_bind()
    permissions = sa.table("permissions", sa.column("id"), sa.column("code"), sa.column("description"))
    roles = sa.table("roles", sa.column("id"), sa.column("name"))
    role_permissions = sa.table("role_permissions", sa.column("role_id"), sa.column("permission_id"))

    # Keep the role available for facilities that use a dedicated cashier.
    cashier_role = bind.execute(sa.select(roles.c.id).where(roles.c.name == "Cashier")).scalar()
    if cashier_role is None:
        cashier_role = uuid4()
        bind.execute(
            sa.insert(roles).values(
                id=cashier_role,
                name="Cashier",
                description="Facility cashier and patient payment operations",
            )
        )

    for code, description, role_names in DEFINITIONS:
        permission_id = bind.execute(sa.select(permissions.c.id).where(permissions.c.code == code)).scalar()
        if permission_id is None:
            permission_id = uuid4()
            bind.execute(
                sa.insert(permissions).values(id=permission_id, code=code, description=description)
            )

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
                bind.execute(
                    sa.insert(role_permissions).values(
                        role_id=role_id,
                        permission_id=permission_id,
                    )
                )


def downgrade() -> None:
    bind = op.get_bind()
    permissions = sa.table("permissions", sa.column("id"), sa.column("code"))
    role_permissions = sa.table("role_permissions", sa.column("permission_id"))
    roles = sa.table("roles", sa.column("id"), sa.column("name"))

    codes = [code for code, _, _ in DEFINITIONS]
    rows = bind.execute(sa.select(permissions.c.id).where(permissions.c.code.in_(codes))).fetchall()
    for row in rows:
        bind.execute(sa.delete(role_permissions).where(role_permissions.c.permission_id == row.id))
        bind.execute(sa.delete(permissions).where(permissions.c.id == row.id))

    # Only remove the role if it has never been assigned to staff.
    cashier_id = bind.execute(sa.select(roles.c.id).where(roles.c.name == "Cashier")).scalar()
    if cashier_id is not None:
        staff_roles = sa.table("staff_roles", sa.column("role_id"))
        assigned = bind.execute(sa.select(staff_roles.c.role_id).where(staff_roles.c.role_id == cashier_id)).first()
        if assigned is None:
            bind.execute(sa.delete(roles).where(roles.c.id == cashier_id))
