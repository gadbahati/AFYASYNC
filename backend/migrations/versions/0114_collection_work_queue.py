"""financial collection work queue
Revision ID: 0114_collection_work_queue
Revises: 0113_revenue_anomalies
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision="0114_collection_work_queue"
down_revision="0113_revenue_anomalies"
branch_labels=None
depends_on=None

def upgrade():
    op.create_table(
        "collection_work_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("facility_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("facilities.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("source_type", sa.String(40), nullable=False),
        sa.Column("source_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(220), nullable=False),
        sa.Column("priority", sa.String(20), nullable=False, server_default="NORMAL"),
        sa.Column("status", sa.String(30), nullable=False, server_default="OPEN"),
        sa.Column("assigned_to", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("due_at", sa.DateTime(timezone=True)),
        sa.Column("outstanding_amount", sa.Numeric(14,2), nullable=False, server_default="0"),
        sa.Column("note", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_collection_work_items_facility_status", "collection_work_items", ["facility_id","status"])
    op.create_index("ix_collection_work_items_priority", "collection_work_items", ["facility_id","priority"])
    op.create_index("ix_collection_work_items_source", "collection_work_items", ["source_type","source_id"])

def downgrade():
    op.drop_index("ix_collection_work_items_source", table_name="collection_work_items")
    op.drop_index("ix_collection_work_items_priority", table_name="collection_work_items")
    op.drop_index("ix_collection_work_items_facility_status", table_name="collection_work_items")
    op.drop_table("collection_work_items")
