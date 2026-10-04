"""Phase 162: governed cross-facility MPI and record access permission."""

from uuid import uuid4

from alembic import op
import sqlalchemy as sa

revision = "0132_cross_facility_mpi"
down_revision = "0131_clinical_orders"
branch_labels = None
depends_on = None

PERMISSION_CODE = "interoperability.patient.read"
DESCRIPTION = "Resolve patient identity and read governed cross-facility patient records"
ROLE_NAMES = {"National Health Administrator", "System Administrator"}


def upgrade() -> None:
    bind = op.get_bind()
    permissions = sa.table(
        "permissions", sa.column("id"), sa.column("code"), sa.column("description")
    )
    roles = sa.table("roles", sa.column("id"), sa.column("name"))
    role_permissions = sa.table(
        "role_permissions", sa.column("role_id"), sa.column("permission_id")
    )

    permission_id = bind.execute(
        sa.select(permissions.c.id).where(permissions.c.code == PERMISSION_CODE)
    ).scalar()
    if permission_id is None:
        permission_id = uuid4()
        bind.execute(
            sa.insert(permissions).values(
                id=permission_id, code=PERMISSION_CODE, description=DESCRIPTION
            )
        )

    role_rows = bind.execute(
        sa.select(roles.c.id).where(roles.c.name.in_(ROLE_NAMES))
    ).fetchall()
    for row in role_rows:
        exists = bind.execute(
            sa.select(role_permissions.c.role_id).where(
                role_permissions.c.role_id == row.id,
                role_permissions.c.permission_id == permission_id,
            )
        ).first()
        if exists is None:
            bind.execute(
                sa.insert(role_permissions).values(
                    role_id=row.id, permission_id=permission_id
                )
            )


def downgrade() -> None:
    bind = op.get_bind()
    permissions = sa.table("permissions", sa.column("id"), sa.column("code"))
    role_permissions = sa.table("role_permissions", sa.column("permission_id"))
    permission_id = bind.execute(
        sa.select(permissions.c.id).where(permissions.c.code == PERMISSION_CODE)
    ).scalar()
    if permission_id is not None:
        bind.execute(
            sa.delete(role_permissions).where(
                role_permissions.c.permission_id == permission_id
            )
        )
        bind.execute(
            sa.delete(permissions).where(permissions.c.id == permission_id)
        )
