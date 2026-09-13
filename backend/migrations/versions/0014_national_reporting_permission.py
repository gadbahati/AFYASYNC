"""add explicitly privileged national reporting access

Revision ID: 0014_national_reporting_permission
Revises: 0013_integration_facility_scope
"""

from uuid import uuid4

from alembic import op
import sqlalchemy as sa

revision = "0014_national_reporting_permission"
down_revision = "0013_integration_facility_scope"
branch_labels = None
depends_on = None

PERMISSION_CODE = "reports.national.read"
ROLE_NAME = "National Health Administrator"


def upgrade() -> None:
    bind = op.get_bind()
    permissions = sa.table(
        "permissions",
        sa.column("id"),
        sa.column("code"),
        sa.column("description"),
    )
    roles = sa.table("roles", sa.column("id"), sa.column("name"), sa.column("description"))
    role_permissions = sa.table(
        "role_permissions",
        sa.column("role_id"),
        sa.column("permission_id"),
    )

    permission_id = bind.execute(
        sa.select(permissions.c.id).where(permissions.c.code == PERMISSION_CODE)
    ).scalar()
    if permission_id is None:
        permission_id = uuid4()
        bind.execute(
            sa.insert(permissions).values(
                id=permission_id,
                code=PERMISSION_CODE,
                description="View aggregated cross-facility national reporting",
            )
        )

    role_id = bind.execute(
        sa.select(roles.c.id).where(roles.c.name == ROLE_NAME)
    ).scalar()
    if role_id is None:
        role_id = uuid4()
        bind.execute(
            sa.insert(roles).values(
                id=role_id,
                name=ROLE_NAME,
                description="Explicitly privileged access to national cross-facility reporting",
            )
        )

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
    roles = sa.table("roles", sa.column("id"), sa.column("name"))
    role_permissions = sa.table(
        "role_permissions",
        sa.column("role_id"),
        sa.column("permission_id"),
    )

    permission_id = bind.execute(
        sa.select(permissions.c.id).where(permissions.c.code == PERMISSION_CODE)
    ).scalar()
    role_id = bind.execute(
        sa.select(roles.c.id).where(roles.c.name == ROLE_NAME)
    ).scalar()

    if role_id is not None and permission_id is not None:
        bind.execute(
            sa.delete(role_permissions).where(
                role_permissions.c.role_id == role_id,
                role_permissions.c.permission_id == permission_id,
            )
        )
    if role_id is not None:
        bind.execute(sa.delete(roles).where(roles.c.id == role_id))
    if permission_id is not None:
        bind.execute(sa.delete(permissions).where(permissions.c.id == permission_id))
