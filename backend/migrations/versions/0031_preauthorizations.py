"""add SHA preauthorizations

Revision ID: 0031_preauthorizations
Revises: 0030_admissions
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0031_preauthorizations"
down_revision = "0030_admissions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "preauthorizations",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("authorization_number", sa.String(length=80), nullable=False),
        sa.Column("patient_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("facility_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("encounter_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("coverage_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("payer_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("benefit_package_code", sa.String(length=80), nullable=False),
        sa.Column("care_setting", sa.String(length=20), nullable=False),
        sa.Column("department", sa.String(length=50), nullable=False),
        sa.Column("requested_services", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("requested_amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("approved_amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("external_reference", sa.String(length=150), nullable=True),
        sa.Column("requested_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["patient_id"], ["persons.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["facility_id"], ["facilities.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["encounter_id"], ["encounters.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["coverage_id"], ["coverage.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["payer_id"], ["payers.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("authorization_number"),
    )
    op.create_index("ix_preauthorizations_patient_id", "preauthorizations", ["patient_id"])
    op.create_index("ix_preauthorizations_facility_id", "preauthorizations", ["facility_id"])
    op.create_index("ix_preauthorizations_encounter_id", "preauthorizations", ["encounter_id"])
    op.create_index("ix_preauthorizations_coverage_id", "preauthorizations", ["coverage_id"])
    op.create_index("ix_preauthorizations_payer_id", "preauthorizations", ["payer_id"])
    op.create_index("ix_preauthorizations_status", "preauthorizations", ["status"])


def downgrade() -> None:
    op.drop_index("ix_preauthorizations_status", table_name="preauthorizations")
    op.drop_index("ix_preauthorizations_payer_id", table_name="preauthorizations")
    op.drop_index("ix_preauthorizations_coverage_id", table_name="preauthorizations")
    op.drop_index("ix_preauthorizations_encounter_id", table_name="preauthorizations")
    op.drop_index("ix_preauthorizations_facility_id", table_name="preauthorizations")
    op.drop_index("ix_preauthorizations_patient_id", table_name="preauthorizations")
    op.drop_table("preauthorizations")
