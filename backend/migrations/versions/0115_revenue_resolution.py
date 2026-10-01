"""Phase 63 revenue resolution operations
Revision ID: 0115_revenue_resolution
Revises: 0114_collection_work_queue
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0115_revenue_resolution"
down_revision = "0114_collection_work_queue"
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        "revenue_resolution_cases",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("case_number", sa.String(90), nullable=False, unique=True),
        sa.Column("facility_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("facilities.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("source_type", sa.String(40), nullable=False),
        sa.Column("source_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("claim_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("claims.id", ondelete="SET NULL"), nullable=True),
        sa.Column("payer_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("payers.id", ondelete="SET NULL"), nullable=True),
        sa.Column("patient_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("persons.id", ondelete="SET NULL"), nullable=True),
        sa.Column("title", sa.String(220), nullable=False),
        sa.Column("priority", sa.String(20), nullable=False, server_default="MEDIUM"),
        sa.Column("status", sa.String(30), nullable=False, server_default="OPEN"),
        sa.Column("assigned_to", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("amount_at_risk", sa.Numeric(14,2), nullable=False, server_default="0"),
        sa.Column("root_cause", sa.String(80), nullable=True),
        sa.Column("resolution_action", sa.Text(), nullable=True),
        sa.Column("external_reference", sa.String(180), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_revenue_resolution_facility_status", "revenue_resolution_cases", ["facility_id","status"])
    op.create_index("ix_revenue_resolution_priority", "revenue_resolution_cases", ["priority"])
    op.create_index("ix_revenue_resolution_source", "revenue_resolution_cases", ["facility_id","source_type","source_id"])
    op.create_table(
        "revenue_resolution_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("case_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("revenue_resolution_cases.id", ondelete="CASCADE"), nullable=False),
        sa.Column("event_type", sa.String(60), nullable=False),
        sa.Column("from_status", sa.String(30), nullable=True),
        sa.Column("to_status", sa.String(30), nullable=True),
        sa.Column("actor_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("metadata_json", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_revenue_resolution_events_case", "revenue_resolution_events", ["case_id","created_at"])

def downgrade():
    op.drop_index("ix_revenue_resolution_events_case", table_name="revenue_resolution_events")
    op.drop_table("revenue_resolution_events")
    op.drop_index("ix_revenue_resolution_source", table_name="revenue_resolution_cases")
    op.drop_index("ix_revenue_resolution_priority", table_name="revenue_resolution_cases")
    op.drop_index("ix_revenue_resolution_facility_status", table_name="revenue_resolution_cases")
    op.drop_table("revenue_resolution_cases")
