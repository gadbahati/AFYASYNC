"""Add preauthorization workflow foundation.

Revision ID: 0053_preauthorization_foundation
Revises: 0052_national_identity_access
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0053_preauthorization_foundation"
down_revision = "0052_national_identity_access"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "preauthorizations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("patient_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("persons.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("facility_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("facilities.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("coverage_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("coverage.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("payer_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("payers.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("service_code", sa.String(80), nullable=False),
        sa.Column("service_type", sa.String(60), nullable=False),
        sa.Column("requested_amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="PENDING"),
        sa.Column("reason", sa.String(500), nullable=False),
        sa.Column("external_reference", sa.String(150), nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_preauthorizations_patient_id", "preauthorizations", ["patient_id"])
    op.create_index("ix_preauthorizations_facility_id", "preauthorizations", ["facility_id"])
    op.create_index("ix_preauthorizations_coverage_id", "preauthorizations", ["coverage_id"])
    op.create_index("ix_preauthorizations_status", "preauthorizations", ["status"])


def downgrade() -> None:
    op.drop_index("ix_preauthorizations_status", table_name="preauthorizations")
    op.drop_index("ix_preauthorizations_coverage_id", table_name="preauthorizations")
    op.drop_index("ix_preauthorizations_facility_id", table_name="preauthorizations")
    op.drop_index("ix_preauthorizations_patient_id", table_name="preauthorizations")
    op.drop_table("preauthorizations")
