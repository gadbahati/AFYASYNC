"""add laboratory workflow

Revision ID: 0007_laboratory
Revises: 0006_clinical
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0007_laboratory"
down_revision = "0006_clinical"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table("lab_tests",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("code", sa.String(50), nullable=False, unique=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("category", sa.String(100)), sa.Column("sample_type", sa.String(100)),
        sa.Column("status", sa.String(30), nullable=False, server_default="ACTIVE"))
    op.create_index("ix_lab_tests_code", "lab_tests", ["code"])
    op.create_table("lab_orders",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("order_id", sa.String(50), nullable=False, unique=True),
        sa.Column("encounter_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("encounters.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("patient_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("persons.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("ordered_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("staff.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("priority", sa.String(20), nullable=False, server_default="NORMAL"),
        sa.Column("status", sa.String(30), nullable=False, server_default="ORDERED"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False))
    op.create_index("ix_lab_orders_encounter_id", "lab_orders", ["encounter_id"])
    op.create_index("ix_lab_orders_patient_id", "lab_orders", ["patient_id"])
    op.create_index("ix_lab_orders_order_id", "lab_orders", ["order_id"])
    op.create_table("lab_order_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("lab_order_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("lab_orders.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("test_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("lab_tests.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("instructions", sa.Text()), sa.Column("status", sa.String(30), nullable=False, server_default="ORDERED")))
    op.create_index("ix_lab_order_items_lab_order_id", "lab_order_items", ["lab_order_id"])
    op.create_table("lab_samples",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("sample_id", sa.String(50), nullable=False, unique=True),
        sa.Column("lab_order_item_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("lab_order_items.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("collected_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("staff.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("collected_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True)), sa.Column("status", sa.String(30), nullable=False, server_default="COLLECTED")))
    op.create_index("ix_lab_samples_lab_order_item_id", "lab_samples", ["lab_order_item_id"])
    op.create_table("lab_results",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("lab_order_item_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("lab_order_items.id", ondelete="RESTRICT"), nullable=False, unique=True),
        sa.Column("sample_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("lab_samples.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("result", sa.Text(), nullable=False), sa.Column("unit", sa.String(50)),
        sa.Column("reference_range", sa.String(100)), sa.Column("comments", sa.Text()),
        sa.Column("entered_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("staff.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("verified_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("staff.id", ondelete="RESTRICT")),
        sa.Column("status", sa.String(30), nullable=False, server_default="ENTERED"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("verified_at", sa.DateTime(timezone=True)))
    op.create_index("ix_lab_results_lab_order_item_id", "lab_results", ["lab_order_item_id"])


def downgrade() -> None:
    op.drop_table("lab_results"); op.drop_table("lab_samples"); op.drop_table("lab_order_items"); op.drop_table("lab_orders"); op.drop_index("ix_lab_tests_code", table_name="lab_tests"); op.drop_table("lab_tests")
