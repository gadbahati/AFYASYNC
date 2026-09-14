"""add clinical encounter records

Revision ID: 0006_clinical
Revises: 0005_appointments_encounters
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0006_clinical"
down_revision = "0005_appointments_encounters"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "clinical_notes",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("encounter_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("patient_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("facility_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("author_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("note_type", sa.String(length=50), nullable=False),
        sa.Column("subjective", sa.Text(), nullable=True),
        sa.Column("objective", sa.Text(), nullable=True),
        sa.Column("assessment", sa.Text(), nullable=True),
        sa.Column("plan", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["encounter_id"], ["encounters.id"]),
        sa.ForeignKeyConstraint(["patient_id"], ["persons.id"]),
        sa.ForeignKeyConstraint(["facility_id"], ["facilities.id"]),
        sa.ForeignKeyConstraint(["author_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_clinical_notes_encounter_id", "clinical_notes", ["encounter_id"])
    op.create_index("ix_clinical_notes_patient_id", "clinical_notes", ["patient_id"])
    op.create_index("ix_clinical_notes_facility_id", "clinical_notes", ["facility_id"])


def downgrade() -> None:
    op.drop_index("ix_clinical_notes_facility_id", table_name="clinical_notes")
    op.drop_index("ix_clinical_notes_patient_id", table_name="clinical_notes")
    op.drop_index("ix_clinical_notes_encounter_id", table_name="clinical_notes")
    op.drop_table("clinical_notes")
