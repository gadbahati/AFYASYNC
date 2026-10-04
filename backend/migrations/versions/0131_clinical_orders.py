"""Phase 132: clinical orders (lab / pharmacy / imaging).

Revision ID: 0131_clinical_orders
Revises: 0130_clinical_discharge
Create Date: 2026-10-04
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0131_clinical_orders"
down_revision = "0130_clinical_discharge"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "clinical_orders",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("encounter_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("encounters.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("facility_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("facilities.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("patient_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("persons.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("order_type", sa.String(20), nullable=False),
        sa.Column("code", sa.String(80), nullable=True),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("priority", sa.String(20), nullable=False, server_default="ROUTINE"),
        sa.Column("status", sa.String(30), nullable=False, server_default="ORDERED"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("ordered_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("ordered_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_clinical_orders_encounter_id", "clinical_orders", ["encounter_id"])
    op.create_index("ix_clinical_orders_facility_id", "clinical_orders", ["facility_id"])
    op.create_index("ix_clinical_orders_patient_id", "clinical_orders", ["patient_id"])
    op.create_index("ix_clinical_orders_order_type", "clinical_orders", ["order_type"])
    op.create_index("ix_clinical_orders_status", "clinical_orders", ["status"])


def downgrade() -> None:
    op.drop_index("ix_clinical_orders_status", table_name="clinical_orders")
    op.drop_index("ix_clinical_orders_order_type", table_name="clinical_orders")
    op.drop_index("ix_clinical_orders_patient_id", table_name="clinical_orders")
    op.drop_index("ix_clinical_orders_facility_id", table_name="clinical_orders")
    op.drop_index("ix_clinical_orders_encounter_id", table_name="clinical_orders")
    op.drop_table("clinical_orders")
