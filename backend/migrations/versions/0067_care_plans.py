"""add patient care plans for longitudinal clinical care

Revision ID: 0067_care_plans
Revises: 0065_national_facility_registry
"""

from alembic import op
import sqlalchemy as sa

revision = "0067_care_plans"
down_revision = "0065_national_facility_registry"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "care_plans",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("patient_id", sa.UUID(), nullable=False),
        sa.Column("facility_id", sa.UUID(), nullable=False),
        sa.Column("encounter_id", sa.UUID(), nullable=True),
        sa.Column("created_by", sa.UUID(), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("goals", sa.Text(), nullable=True),
        sa.Column("interventions", sa.Text(), nullable=True),
        sa.Column("clinical_notes", sa.Text(), nullable=True),
        sa.Column("target_date", sa.Date(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="ACTIVE"),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["patient_id"], ["persons.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["facility_id"], ["facilities.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["encounter_id"], ["encounters.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    for name, columns in {
        "ix_care_plans_patient_id": ["patient_id"],
        "ix_care_plans_facility_id": ["facility_id"],
        "ix_care_plans_encounter_id": ["encounter_id"],
        "ix_care_plans_status": ["status"],
        "ix_care_plans_facility_patient_status": ["facility_id", "patient_id", "status"],
    }.items():
        op.create_index(name, "care_plans", columns)


def downgrade() -> None:
    for name in ["ix_care_plans_facility_patient_status", "ix_care_plans_status", "ix_care_plans_encounter_id", "ix_care_plans_facility_id", "ix_care_plans_patient_id"]:
        op.drop_index(name, table_name="care_plans")
    op.drop_table("care_plans")
