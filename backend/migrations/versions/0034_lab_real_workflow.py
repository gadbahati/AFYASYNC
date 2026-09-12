"""persist laboratory billing and clinician handoff state

Revision ID: 0034_lab_real_workflow
Revises: 0033_merge_lab_and_patient_identity
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0034_lab_real_workflow"
down_revision = "0033_merge_lab_and_patient_identity"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("lab_orders", sa.Column("forwarded_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("lab_orders", sa.Column("forwarded_by", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key("fk_lab_orders_forwarded_by_staff", "lab_orders", "staff", ["forwarded_by"], ["id"], ondelete="RESTRICT")
    op.add_column("lab_order_items", sa.Column("charge_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key("fk_lab_order_items_charge", "lab_order_items", "charges", ["charge_id"], ["id"], ondelete="RESTRICT")
    op.create_unique_constraint("uq_lab_order_items_charge_id", "lab_order_items", ["charge_id"])


def downgrade() -> None:
    op.drop_constraint("uq_lab_order_items_charge_id", "lab_order_items", type_="unique")
    op.drop_constraint("fk_lab_order_items_charge", "lab_order_items", type_="foreignkey")
    op.drop_column("lab_order_items", "charge_id")
    op.drop_constraint("fk_lab_orders_forwarded_by_staff", "lab_orders", type_="foreignkey")
    op.drop_column("lab_orders", "forwarded_by")
    op.drop_column("lab_orders", "forwarded_at")
