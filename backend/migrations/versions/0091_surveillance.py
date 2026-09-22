"""notifiable events for surveillance

Revision ID: 0091_surveillance
Revises: 0090_ambulance
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0091_surveillance"
down_revision = "0090_ambulance"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "notifiable_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("facility_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("facilities.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("person_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("persons.id", ondelete="SET NULL"), nullable=True),
        sa.Column("condition_code", sa.String(40), nullable=False),
        sa.Column("condition_name", sa.String(120), nullable=False),
        sa.Column("onset_date", sa.Date(), nullable=True),
        sa.Column("notification_date", sa.Date(), nullable=False),
        sa.Column("classification", sa.String(30), nullable=False, server_default="SUSPECTED"),
        sa.Column("status", sa.String(30), nullable=False, server_default="OPEN"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("reported_by_staff_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("staff.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_notifiable_events_facility_id", "notifiable_events", ["facility_id"])
    op.create_index("ix_notifiable_events_person_id", "notifiable_events", ["person_id"])
    op.create_index("ix_notifiable_status", "notifiable_events", ["status"])
    op.create_index("ix_notifiable_condition", "notifiable_events", ["condition_code"])
    op.create_index("ix_notifiable_facility_status", "notifiable_events", ["facility_id", "status"])


def downgrade() -> None:
    op.drop_table("notifiable_events")
