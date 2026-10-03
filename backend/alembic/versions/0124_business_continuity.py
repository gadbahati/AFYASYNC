"""Phase 120 business continuity controls.

Revision ID: 0124_business_continuity
Revises: 0123_multi_tenant_control_plane
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0124_business_continuity"
down_revision = "0123_multi_tenant_control_plane"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "business_continuity_plans",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("service_tier", sa.String(30), nullable=False, server_default="CRITICAL"),
        sa.Column("rto_minutes", sa.Integer(), nullable=False, server_default="240"),
        sa.Column("rpo_minutes", sa.Integer(), nullable=False, server_default="60"),
        sa.Column("offline_max_hours", sa.Integer(), nullable=False, server_default="24"),
        sa.Column("backup_cadence_minutes", sa.Integer(), nullable=False, server_default="1440"),
        sa.Column("status", sa.String(30), nullable=False, server_default="DRAFT"),
        sa.Column("owner_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("last_tested_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_bcp_org_status", "business_continuity_plans", ["organization_id", "status"])
    op.create_index("ix_bcp_status", "business_continuity_plans", ["status"])

    op.create_table(
        "business_continuity_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("plan_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("business_continuity_plans.id", ondelete="CASCADE"), nullable=False),
        sa.Column("event_type", sa.String(40), nullable=False),
        sa.Column("result", sa.String(30), nullable=False),
        sa.Column("measured_rto_minutes", sa.Integer(), nullable=True),
        sa.Column("measured_rpo_minutes", sa.Integer(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("actor_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_bcp_event_plan_created", "business_continuity_events", ["plan_id", "created_at"])


def downgrade():
    op.drop_index("ix_bcp_event_plan_created", table_name="business_continuity_events")
    op.drop_table("business_continuity_events")
    op.drop_index("ix_bcp_status", table_name="business_continuity_plans")
    op.drop_index("ix_bcp_org_status", table_name="business_continuity_plans")
    op.drop_table("business_continuity_plans")
