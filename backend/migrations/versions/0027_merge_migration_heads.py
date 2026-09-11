"""merge previously independent migration branches

Revision ID: 0027_merge_migration_heads
Revises: 0026_post_hardening_permissions, 0016_patient_access_permissions,
         0016_patient_record_permission, 0016_patient_record_write_permission,
         0015_department_write_permission

This is a graph-only merge revision. The individual branches contain the
actual schema and permission changes; this revision makes Alembic's upgrade
path converge on one head so fresh and existing databases receive every
branch instead of silently leaving patient/facility migrations unapplied.
"""

from alembic import op

revision = "0027_merge_migration_heads"
down_revision = (
    "0026_post_hardening_permissions",
    "0016_patient_access_permissions",
    "0016_patient_record_permission",
    "0016_patient_record_write_permission",
    "0015_department_write_permission",
)
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
