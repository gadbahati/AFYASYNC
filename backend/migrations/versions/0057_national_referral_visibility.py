"""Add explicit national referral visibility permission.

Revision ID: 0057_national_referral_visibility
Revises: 0056_merge_national_supply_heads
"""
from uuid import uuid4

from alembic import op
import sqlalchemy as sa

revision = "0057_national_referral_visibility"
down_revision = "0056_merge_national_supply_heads"
branch_labels = None
depends_on = None

PERMISSION_CODE = "referral.network.read"
ROLE_NAME = "National Health Referral Administrator"


def upgrade() -> None:
    """Seed the permission and privileged role with compact, idempotent SQL.

    Keeping this migration to three short statements avoids ORM/table metadata
    work during the deployment migration transaction while preserving the
    intended RBAC state on both fresh and existing databases.
    """
    permission_id = uuid4()
    role_id = uuid4()
    bind = op.get_bind()

    bind.execute(
        sa.text(
            """
            INSERT INTO permissions (id, code, description)
            VALUES (:permission_id, :code, :description)
            ON CONFLICT (code) DO NOTHING
            """
        ),
        {
            "permission_id": permission_id,
            "code": PERMISSION_CODE,
            "description": "View privacy-minimized referral routing and operational status across active facilities",
        },
    )

    bind.execute(
        sa.text(
            """
            INSERT INTO roles (id, name, description)
            VALUES (:role_id, :name, :description)
            ON CONFLICT (name) DO NOTHING
            """
        ),
        {
            "role_id": role_id,
            "name": ROLE_NAME,
            "description": "Explicitly privileged national referral visibility",
        },
    )

    bind.execute(
        sa.text(
            """
            INSERT INTO role_permissions (role_id, permission_id)
            SELECT r.id, p.id
            FROM roles r
            CROSS JOIN permissions p
            WHERE r.name = :role_name
              AND p.code = :permission_code
            ON CONFLICT (role_id, permission_id) DO NOTHING
            """
        ),
        {"role_name": ROLE_NAME, "permission_code": PERMISSION_CODE},
    )


def downgrade() -> None:
    bind = op.get_bind()
    bind.execute(
        sa.text(
            """
            DELETE FROM role_permissions
            WHERE role_id = (SELECT id FROM roles WHERE name = :role_name)
              AND permission_id = (SELECT id FROM permissions WHERE code = :permission_code)
            """
        ),
        {"role_name": ROLE_NAME, "permission_code": PERMISSION_CODE},
    )
    bind.execute(
        sa.text("DELETE FROM roles WHERE name = :role_name"),
        {"role_name": ROLE_NAME},
    )
    bind.execute(
        sa.text("DELETE FROM permissions WHERE code = :permission_code"),
        {"permission_code": PERMISSION_CODE},
    )
