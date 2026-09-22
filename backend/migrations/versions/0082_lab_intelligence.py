"""lab intelligence references and critical alerts

Revision ID: 0082_lab_intelligence
Revises: 0081_medication_safety_flags
Create Date: 2026-09-22
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0082_lab_intelligence"
down_revision = "0081_medication_safety_flags"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "lab_test_references",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("test_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("lab_tests.id", ondelete="CASCADE"), nullable=False),
        sa.Column("unit", sa.String(50)),
        sa.Column("ref_low", sa.Numeric(18, 6)),
        sa.Column("ref_high", sa.Numeric(18, 6)),
        sa.Column("critical_low", sa.Numeric(18, 6)),
        sa.Column("critical_high", sa.Numeric(18, 6)),
        sa.Column("tat_target_minutes", sa.Integer()),
        sa.Column("sex_specific", sa.String(10)),
        sa.Column("notes", sa.Text()),
        sa.Column("status", sa.String(30), nullable=False, server_default="ACTIVE"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("test_id", name="uq_lab_test_reference_test"),
    )
    op.create_index("ix_lab_test_references_test_id", "lab_test_references", ["test_id"])

    op.create_table(
        "lab_critical_alerts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("lab_result_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("lab_results.id", ondelete="CASCADE"), nullable=False),
        sa.Column("facility_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("facilities.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("patient_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("persons.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("encounter_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("encounters.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("test_code", sa.String(50), nullable=False),
        sa.Column("test_name", sa.String(200), nullable=False),
        sa.Column("result_value", sa.String(100), nullable=False),
        sa.Column("unit", sa.String(50)),
        sa.Column("flag", sa.String(30), nullable=False),
        sa.Column("severity", sa.String(20), nullable=False, server_default="CRITICAL"),
        sa.Column("status", sa.String(30), nullable=False, server_default="OPEN"),
        sa.Column("acknowledged_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("staff.id", ondelete="SET NULL")),
        sa.Column("acknowledged_at", sa.DateTime(timezone=True)),
        sa.Column("ack_note", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("lab_result_id", name="uq_lab_critical_result"),
    )
    op.create_index("ix_lab_critical_alerts_facility_id", "lab_critical_alerts", ["facility_id"])
    op.create_index("ix_lab_critical_alerts_status", "lab_critical_alerts", ["status"])


def downgrade() -> None:
    op.drop_table("lab_critical_alerts")
    op.drop_table("lab_test_references")
