"""add referrals and interfacility transfers

Revision ID: 0023_referrals_transfers
Revises: 0022_external_reference_integrity
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0023_referrals_transfers"
down_revision = "0022_external_reference_integrity"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "referrals",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("referral_id", sa.String(70), nullable=False, unique=True),
        sa.Column("patient_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("persons.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("encounter_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("encounters.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("source_facility_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("facilities.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("destination_facility_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("facilities.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("destination_department_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("departments.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("referred_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("staff.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("priority", sa.String(20), nullable=False, server_default="ROUTINE"),
        sa.Column("clinical_summary", sa.Text(), nullable=True),
        sa.Column("status", sa.String(30), nullable=False, server_default="CREATED"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_referrals_patient_id", "referrals", ["patient_id"])
    op.create_index("ix_referrals_encounter_id", "referrals", ["encounter_id"])
    op.create_index("ix_referrals_source_facility_id", "referrals", ["source_facility_id"])
    op.create_index("ix_referrals_destination_facility_id", "referrals", ["destination_facility_id"])
    op.create_index("ix_referrals_destination_department_id", "referrals", ["destination_department_id"])
    op.create_index("ix_referrals_status", "referrals", ["status"])

    op.create_table(
        "transfers",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("transfer_id", sa.String(70), nullable=False, unique=True),
        sa.Column("referral_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("referrals.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("patient_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("persons.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("encounter_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("encounters.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("source_facility_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("facilities.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("destination_facility_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("facilities.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("requested_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("staff.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="REQUESTED"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_transfers_referral_id", "transfers", ["referral_id"])
    op.create_index("ix_transfers_patient_id", "transfers", ["patient_id"])
    op.create_index("ix_transfers_encounter_id", "transfers", ["encounter_id"])
    op.create_index("ix_transfers_source_facility_id", "transfers", ["source_facility_id"])
    op.create_index("ix_transfers_destination_facility_id", "transfers", ["destination_facility_id"])
    op.create_index("ix_transfers_status", "transfers", ["status"])


def downgrade() -> None:
    op.drop_index("ix_transfers_status", table_name="transfers")
    op.drop_index("ix_transfers_destination_facility_id", table_name="transfers")
    op.drop_index("ix_transfers_source_facility_id", table_name="transfers")
    op.drop_index("ix_transfers_encounter_id", table_name="transfers")
    op.drop_index("ix_transfers_patient_id", table_name="transfers")
    op.drop_index("ix_transfers_referral_id", table_name="transfers")
    op.drop_table("transfers")
    op.drop_index("ix_referrals_status", table_name="referrals")
    op.drop_index("ix_referrals_destination_department_id", table_name="referrals")
    op.drop_index("ix_referrals_destination_facility_id", table_name="referrals")
    op.drop_index("ix_referrals_source_facility_id", table_name="referrals")
    op.drop_index("ix_referrals_encounter_id", table_name="referrals")
    op.drop_index("ix_referrals_patient_id", table_name="referrals")
    op.drop_table("referrals")
