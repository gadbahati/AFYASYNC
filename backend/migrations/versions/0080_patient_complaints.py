"""patient complaints for Afya Citizen

Revision ID: 0080_patient_complaints
Revises: 0079_benefit_utilisation
Create Date: 2026-09-22
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0080_patient_complaints"
down_revision = "0079_benefit_utilisation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "patient_complaints",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("person_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("persons.id", ondelete="CASCADE"), nullable=False),
        sa.Column("category", sa.String(40), nullable=False),
        sa.Column("subject", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("related_encounter_id", postgresql.UUID(as_uuid=True)),
        sa.Column("related_claim_ref", sa.String(100)),
        sa.Column("status", sa.String(30), nullable=False, server_default="OPEN"),
        sa.Column("resolution_note", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_patient_complaints_person_id", "patient_complaints", ["person_id"])
    op.create_index("ix_patient_complaints_category", "patient_complaints", ["category"])
    op.create_index("ix_patient_complaints_status", "patient_complaints", ["status"])


def downgrade() -> None:
    op.drop_table("patient_complaints")
