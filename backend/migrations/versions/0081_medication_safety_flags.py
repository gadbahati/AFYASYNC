"""medication safety flags

Revision ID: 0081_medication_safety_flags
Revises: 0080_patient_complaints
Create Date: 2026-09-22
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0081_medication_safety_flags"
down_revision = "0080_patient_complaints"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "medication_safety_flags",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("medication_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("medications.id", ondelete="CASCADE"), nullable=False),
        sa.Column("high_risk", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("black_box", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("pregnancy_category", sa.String(10)),
        sa.Column("paediatric_caution", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("renal_caution", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("notes", sa.Text()),
        sa.Column("status", sa.String(30), nullable=False, server_default="ACTIVE"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("medication_id", name="uq_med_safety_medication"),
    )
    op.create_index("ix_medication_safety_flags_medication_id", "medication_safety_flags", ["medication_id"])


def downgrade() -> None:
    op.drop_table("medication_safety_flags")
