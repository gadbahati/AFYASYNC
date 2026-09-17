"""add patient allergy clinical safety records

Revision ID: 0069_allergies
Revises: 0068_care_plan_permissions
"""

from alembic import op
import sqlalchemy as sa

revision = "0069_allergies"
down_revision = "0068_care_plan_permissions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "allergies",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("patient_id", sa.UUID(), nullable=False),
        sa.Column("facility_id", sa.UUID(), nullable=False),
        sa.Column("recorded_by", sa.UUID(), nullable=False),
        sa.Column("allergen", sa.String(length=200), nullable=False),
        sa.Column("reaction", sa.Text(), nullable=True),
        sa.Column("severity", sa.String(length=20), nullable=False, server_default="UNKNOWN"),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="ACTIVE"),
        sa.Column("onset_date", sa.Date(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["patient_id"], ["persons.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["facility_id"], ["facilities.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["recorded_by"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    for name, columns in {
        "ix_allergies_patient_id": ["patient_id"],
        "ix_allergies_facility_id": ["facility_id"],
        "ix_allergies_status": ["status"],
        "ix_allergies_facility_patient_status": ["facility_id", "patient_id", "status"],
    }.items():
        op.create_index(name, "allergies", columns)


def downgrade() -> None:
    for name in ["ix_allergies_facility_patient_status", "ix_allergies_status", "ix_allergies_facility_id", "ix_allergies_patient_id"]:
        op.drop_index(name, table_name="allergies")
    op.drop_table("allergies")
