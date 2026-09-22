"""hie export logs

Revision ID: 0085_hie_export_logs
Revises: 0084_pharmacy_supply
Create Date: 2026-09-22
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0085_hie_export_logs"
down_revision = "0084_pharmacy_supply"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "hie_export_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("facility_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("facilities.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("patient_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("persons.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("export_type", sa.String(50), nullable=False),
        sa.Column("resource_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("actor_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("purpose", sa.String(200)),
        sa.Column("destination", sa.String(200)),
        sa.Column("status", sa.String(30), nullable=False, server_default="SUCCESS"),
        sa.Column("notes", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_hie_export_logs_facility_id", "hie_export_logs", ["facility_id"])
    op.create_index("ix_hie_export_logs_patient_id", "hie_export_logs", ["patient_id"])


def downgrade() -> None:
    op.drop_table("hie_export_logs")
