"""Phase 131: clinical encounter discharge records.

Revision ID: 0130_clinical_discharge
Revises: 0129_government_identity_mfa
Create Date: 2026-10-04
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0130_clinical_discharge"
down_revision = "0129_government_identity_mfa"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "clinical_discharges",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("encounter_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("encounters.id", ondelete="RESTRICT"), nullable=False, unique=True),
        sa.Column("facility_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("facilities.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("patient_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("persons.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("disposition", sa.String(40), nullable=False),
        sa.Column("outcome", sa.String(40), nullable=False, server_default="STABLE"),
        sa.Column("follow_up_instructions", sa.Text(), nullable=True),
        sa.Column("follow_up_date", sa.Date(), nullable=True),
        sa.Column("discharge_summary", sa.Text(), nullable=True),
        sa.Column("discharged_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("discharged_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_clinical_discharges_facility_id", "clinical_discharges", ["facility_id"])
    op.create_index("ix_clinical_discharges_patient_id", "clinical_discharges", ["patient_id"])
    op.create_index("ix_clinical_discharges_disposition", "clinical_discharges", ["disposition"])


def downgrade() -> None:
    op.drop_index("ix_clinical_discharges_disposition", table_name="clinical_discharges")
    op.drop_index("ix_clinical_discharges_patient_id", table_name="clinical_discharges")
    op.drop_index("ix_clinical_discharges_facility_id", table_name="clinical_discharges")
    op.drop_table("clinical_discharges")
