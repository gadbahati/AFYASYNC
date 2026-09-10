"""scope integrations to facilities

Revision ID: 0013_integration_facility_scope
Revises: 0012_integrations
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0013_integration_facility_scope"
down_revision = "0012_integrations"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "integrations",
        sa.Column("facility_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_integrations_facility_id",
        "integrations",
        "facilities",
        ["facility_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_index("ix_integrations_facility_id", "integrations", ["facility_id"])

    # Existing integrations predate facility scoping. They must be assigned
    # explicitly before production use rather than silently choosing a facility.
    # Keep the column nullable during migration so existing installations can
    # be backfilled safely, then enforce the invariant in application code.


def downgrade() -> None:
    op.drop_index("ix_integrations_facility_id", table_name="integrations")
    op.drop_constraint("fk_integrations_facility_id", "integrations", type_="foreignkey")
    op.drop_column("integrations", "facility_id")
