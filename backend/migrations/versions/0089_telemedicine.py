"""telemedicine consult requests

Revision ID: 0089_telemedicine
Revises: 0088_workforce_credentials
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0089_telemedicine"
down_revision = "0088_workforce_credentials"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "tele_consult_requests",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("person_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("persons.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("facility_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("facilities.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("reason", sa.String(500), nullable=False),
        sa.Column("urgency", sa.String(20), nullable=False, server_default="ROUTINE"),
        sa.Column("status", sa.String(30), nullable=False, server_default="REQUESTED"),
        sa.Column("preferred_window", sa.String(120), nullable=True),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("facility_message", sa.String(500), nullable=True),
        sa.Column("clinical_summary", sa.Text(), nullable=True),
        sa.Column("handled_by_staff_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("staff.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_tele_consult_requests_person_id", "tele_consult_requests", ["person_id"])
    op.create_index("ix_tele_consult_requests_facility_id", "tele_consult_requests", ["facility_id"])
    op.create_index("ix_tele_consult_status", "tele_consult_requests", ["status"])
    op.create_index("ix_tele_consult_facility_status", "tele_consult_requests", ["facility_id", "status"])


def downgrade() -> None:
    op.drop_table("tele_consult_requests")
