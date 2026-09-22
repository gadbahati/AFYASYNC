"""controlled dispense logs

Revision ID: 0084_pharmacy_supply
Revises: 0083_imaging_intelligence
Create Date: 2026-09-22
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0084_pharmacy_supply"
down_revision = "0083_imaging_intelligence"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "controlled_dispense_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("facility_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("facilities.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("patient_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("persons.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("prescription_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("prescriptions.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("medication_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("medications.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("quantity", sa.Numeric(12, 2), nullable=False),
        sa.Column("dispensed_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("staff.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("witness_staff_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("staff.id", ondelete="SET NULL")),
        sa.Column("schedule_class", sa.String(20)),
        sa.Column("notes", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_controlled_dispense_logs_facility_id", "controlled_dispense_logs", ["facility_id"])
    op.create_index("ix_controlled_dispense_logs_patient_id", "controlled_dispense_logs", ["patient_id"])
    op.create_index("ix_controlled_dispense_logs_prescription_id", "controlled_dispense_logs", ["prescription_id"])


def downgrade() -> None:
    op.drop_table("controlled_dispense_logs")
