"""partner interests for sandbox onboarding

Revision ID: 0093_partner_interests
Revises: 0092_erasure_requests
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0093_partner_interests"
down_revision = "0092_erasure_requests"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "partner_interests",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organisation", sa.String(200), nullable=False),
        sa.Column("contact_email", sa.String(200), nullable=False),
        sa.Column("contact_phone", sa.String(40), nullable=True),
        sa.Column("use_case", sa.String(500), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="RECEIVED"),
        sa.Column("facility_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("facilities.id", ondelete="SET NULL"), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("partner_interests")
