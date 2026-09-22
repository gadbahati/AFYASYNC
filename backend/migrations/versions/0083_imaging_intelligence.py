"""imaging intelligence tables

Revision ID: 0083_imaging_intelligence
Revises: 0082_lab_intelligence
Create Date: 2026-09-22
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0083_imaging_intelligence"
down_revision = "0082_lab_intelligence"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "imaging_test_safety",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("test_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("imaging_tests.id", ondelete="CASCADE"), nullable=False),
        sa.Column("requires_contrast", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("contrast_type", sa.String(40)),
        sa.Column("radiation_risk", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("pregnancy_caution", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("notes", sa.Text()),
        sa.Column("status", sa.String(30), nullable=False, server_default="ACTIVE"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("test_id", name="uq_imaging_test_safety_test"),
    )
    op.create_index("ix_imaging_test_safety_test_id", "imaging_test_safety", ["test_id"])

    op.create_table(
        "imaging_critical_findings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("report_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("imaging_reports.id", ondelete="CASCADE"), nullable=False),
        sa.Column("order_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("imaging_orders.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("facility_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("facilities.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("patient_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("persons.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("modality", sa.String(50)),
        sa.Column("test_name", sa.String(200), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("severity", sa.String(20), nullable=False, server_default="CRITICAL"),
        sa.Column("status", sa.String(30), nullable=False, server_default="OPEN"),
        sa.Column("acknowledged_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("staff.id", ondelete="SET NULL")),
        sa.Column("acknowledged_at", sa.DateTime(timezone=True)),
        sa.Column("ack_note", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("report_id", name="uq_imaging_critical_report"),
    )
    op.create_index("ix_imaging_critical_findings_facility_id", "imaging_critical_findings", ["facility_id"])
    op.create_index("ix_imaging_critical_findings_status", "imaging_critical_findings", ["status"])


def downgrade() -> None:
    op.drop_table("imaging_critical_findings")
    op.drop_table("imaging_test_safety")
