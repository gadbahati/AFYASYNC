"""add inpatient admissions

Revision ID: 0030_admissions
Revises: 0029_sha_mch_admissions_benefits
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0030_admissions"
down_revision = "0029_sha_mch_admissions_benefits"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "admissions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("admission_number", sa.String(length=60), nullable=False),
        sa.Column("patient_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("facility_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("encounter_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("benefit_package_code", sa.String(length=80), nullable=False),
        sa.Column("ward", sa.String(length=120), nullable=False),
        sa.Column("bed", sa.String(length=50), nullable=False),
        sa.Column("diagnosis", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("admitted_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("discharged_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["patient_id"], ["persons.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["facility_id"], ["facilities.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["encounter_id"], ["encounters.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("admission_number"),
        sa.UniqueConstraint("encounter_id"),
    )
    op.create_index("ix_admissions_patient_id", "admissions", ["patient_id"])
    op.create_index("ix_admissions_facility_id", "admissions", ["facility_id"])
    op.create_index("ix_admissions_admission_number", "admissions", ["admission_number"])
    op.create_index("ix_admissions_benefit_package_code", "admissions", ["benefit_package_code"])
    op.create_index("ix_admissions_status", "admissions", ["status"])


def downgrade() -> None:
    op.drop_index("ix_admissions_status", table_name="admissions")
    op.drop_index("ix_admissions_benefit_package_code", table_name="admissions")
    op.drop_index("ix_admissions_admission_number", table_name="admissions")
    op.drop_index("ix_admissions_facility_id", table_name="admissions")
    op.drop_index("ix_admissions_patient_id", table_name="admissions")
    op.drop_table("admissions")
