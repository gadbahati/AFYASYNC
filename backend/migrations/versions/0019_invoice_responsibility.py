"""add invoice responsibility breakdown

Revision ID: 0019_invoice_responsibility
Revises: 0018_payer_benefit_rules
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0019_invoice_responsibility"
down_revision = "0018_payer_benefit_rules"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("invoice_items", sa.Column("payer_amount", sa.Numeric(14, 2), nullable=False, server_default="0"))
    op.add_column("invoice_items", sa.Column("patient_amount", sa.Numeric(14, 2), nullable=False, server_default="0"))
    op.add_column("invoice_items", sa.Column("benefit_rule_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key(
        "fk_invoice_items_benefit_rule",
        "invoice_items",
        "payer_benefit_rules",
        ["benefit_rule_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_index("ix_invoice_items_benefit_rule_id", "invoice_items", ["benefit_rule_id"])


def downgrade() -> None:
    op.drop_index("ix_invoice_items_benefit_rule_id", table_name="invoice_items")
    op.drop_constraint("fk_invoice_items_benefit_rule", "invoice_items", type_="foreignkey")
    op.drop_column("invoice_items", "benefit_rule_id")
    op.drop_column("invoice_items", "patient_amount")
    op.drop_column("invoice_items", "payer_amount")
