"""referral booking exchange
Revision ID: 0107_referral_booking
Revises: 0106_care_coordination
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
revision = "0107_referral_booking"
down_revision = "0106_care_coordination"
branch_labels = None
depends_on = None

def upgrade():
    op.create_table("referral_bookings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("booking_reference", sa.String(80), nullable=False, unique=True),
        sa.Column("idempotency_key", sa.String(200), nullable=False, unique=True),
        sa.Column("patient_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("persons.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("source_facility_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("facilities.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("destination_facility_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("facilities.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("referral_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("referrals.id", ondelete="RESTRICT"), nullable=False, unique=True),
        sa.Column("appointment_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("appointments.id", ondelete="RESTRICT"), nullable=False, unique=True),
        sa.Column("coordination_case_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("care_coordination_cases.id", ondelete="RESTRICT"), nullable=False, unique=True),
        sa.Column("service_code", sa.String(80), nullable=False),
        sa.Column("network_code", sa.String(80), nullable=False),
        sa.Column("appointment_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="BOOKED"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_referral_bookings_patient", "referral_bookings", ["patient_id"])
    op.create_index("ix_referral_bookings_source", "referral_bookings", ["source_facility_id"])
    op.create_index("ix_referral_bookings_destination", "referral_bookings", ["destination_facility_id"])
    op.create_index("ix_referral_bookings_service_network", "referral_bookings", ["service_code", "network_code"])
    op.create_index("ix_referral_bookings_appointment_at", "referral_bookings", ["appointment_at"])
    op.create_index("ix_referral_bookings_status", "referral_bookings", ["status"])

def downgrade():
    op.drop_table("referral_bookings")
