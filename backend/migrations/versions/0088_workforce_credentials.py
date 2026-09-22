"""professional credentials for workforce

Revision ID: 0088_workforce_credentials
Revises: 0087_offline_outbox
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0088_workforce_credentials"
down_revision = "0087_offline_outbox"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "professional_credentials",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("staff_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("staff.id", ondelete="CASCADE"), nullable=False),
        sa.Column("facility_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("facilities.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("council_code", sa.String(40), nullable=False),
        sa.Column("cadre", sa.String(80), nullable=False),
        sa.Column("licence_number", sa.String(80), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="ACTIVE"),
        sa.Column("issued_on", sa.Date(), nullable=True),
        sa.Column("expiry_date", sa.Date(), nullable=True),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("staff_id", "council_code", "licence_number", name="uq_credential_staff_council_number"),
    )
    op.create_index("ix_professional_credentials_staff_id", "professional_credentials", ["staff_id"])
    op.create_index("ix_professional_credentials_facility_id", "professional_credentials", ["facility_id"])
    op.create_index("ix_credential_expiry", "professional_credentials", ["expiry_date"])
    op.create_index("ix_credential_status", "professional_credentials", ["status"])


def downgrade() -> None:
    op.drop_table("professional_credentials")
