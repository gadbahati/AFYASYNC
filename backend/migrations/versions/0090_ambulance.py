"""ambulance transport requests

Revision ID: 0090_ambulance
Revises: 0089_telemedicine
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0090_ambulance"
down_revision = "0089_telemedicine"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ambulance_requests",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("person_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("persons.id", ondelete="SET NULL"), nullable=True),
        sa.Column("facility_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("facilities.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("requester_phone", sa.String(30), nullable=False),
        sa.Column("pickup_location", sa.String(300), nullable=False),
        sa.Column("destination", sa.String(300), nullable=True),
        sa.Column("clinical_note", sa.String(500), nullable=True),
        sa.Column("priority", sa.String(20), nullable=False, server_default="ROUTINE"),
        sa.Column("status", sa.String(30), nullable=False, server_default="REQUESTED"),
        sa.Column("vehicle_ref", sa.String(80), nullable=True),
        sa.Column("eta_minutes", sa.Float(), nullable=True),
        sa.Column("dispatcher_message", sa.String(500), nullable=True),
        sa.Column("outcome_note", sa.Text(), nullable=True),
        sa.Column("handled_by_staff_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("staff.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_ambulance_requests_person_id", "ambulance_requests", ["person_id"])
    op.create_index("ix_ambulance_requests_facility_id", "ambulance_requests", ["facility_id"])
    op.create_index("ix_ambulance_status", "ambulance_requests", ["status"])
    op.create_index("ix_ambulance_facility_status", "ambulance_requests", ["facility_id", "status"])


def downgrade() -> None:
    op.drop_table("ambulance_requests")
