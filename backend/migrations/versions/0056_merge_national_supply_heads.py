"""Merge the remaining national-access migration heads.

Revision ID: 0056_merge_national_supply_heads
Revises: 0053_national_supply_planning, 0055_interoperability_clinical_read, 0055_national_supply_visibility
"""

from alembic import op

revision = "0056_merge_national_supply_heads"
down_revision = (
    "0053_national_supply_planning",
    "0055_interoperability_clinical_read",
    "0055_national_supply_visibility",
)
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
