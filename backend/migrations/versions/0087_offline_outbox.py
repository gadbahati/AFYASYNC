"""offline outbox events and connectivity probes

Revision ID: 0087_offline_outbox
Revises: 0086_hie_robust
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0087_offline_outbox"
down_revision = "0086_hie_robust"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "offline_outbox_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("facility_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("facilities.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("event_type", sa.String(80), nullable=False),
        sa.Column("payload", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("idempotency_key", sa.String(120), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="PENDING"),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("max_attempts", sa.Integer(), nullable=False, server_default="8"),
        sa.Column("next_retry_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("facility_id", "idempotency_key", name="uq_offline_outbox_idempotency"),
    )
    op.create_index("ix_offline_outbox_events_facility_id", "offline_outbox_events", ["facility_id"])
    op.create_index("ix_offline_outbox_events_status", "offline_outbox_events", ["status"])
    op.create_index("ix_offline_outbox_events_event_type", "offline_outbox_events", ["event_type"])
    op.create_index("ix_offline_outbox_status_retry", "offline_outbox_events", ["status", "next_retry_at"])
    op.create_index("ix_offline_outbox_facility_created", "offline_outbox_events", ["facility_id", "created_at"])

    op.create_table(
        "offline_connectivity_probes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("facility_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("facilities.id", ondelete="SET NULL"), nullable=True),
        sa.Column("target", sa.String(200), nullable=False),
        sa.Column("ok", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("detail", sa.String(300), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_offline_connectivity_probes_facility_id", "offline_connectivity_probes", ["facility_id"])


def downgrade() -> None:
    op.drop_table("offline_connectivity_probes")
    op.drop_table("offline_outbox_events")
