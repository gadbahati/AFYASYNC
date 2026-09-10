"""persist invoice coverage identity and enforce invoice/claim uniqueness

Revision ID: 0021_invoice_claim_integrity
Revises: 0020_coverage_benefit_permission
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0021_invoice_claim_integrity"
down_revision = "0020_coverage_benefit_permission"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("invoices", sa.Column("coverage_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("invoices", sa.Column("payer_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key("fk_invoices_coverage", "invoices", "coverage", ["coverage_id"], ["id"], ondelete="RESTRICT")
    op.create_foreign_key("fk_invoices_payer", "invoices", "payers", ["payer_id"], ["id"], ondelete="RESTRICT")
    op.create_index("ix_invoices_coverage_id", "invoices", ["coverage_id"])
    op.create_index("ix_invoices_payer_id", "invoices", ["payer_id"])
    op.create_index(
        "uq_invoices_active_encounter",
        "invoices",
        ["facility_id", "encounter_id"],
        unique=True,
        postgresql_where=sa.text("status <> 'VOID'"),
    )
    op.create_index("uq_claims_invoice", "claims", ["invoice_id"], unique=True)


def downgrade() -> None:
    op.drop_index("uq_claims_invoice", table_name="claims")
    op.drop_index("uq_invoices_active_encounter", table_name="invoices")
    op.drop_index("ix_invoices_payer_id", table_name="invoices")
    op.drop_index("ix_invoices_coverage_id", table_name="invoices")
    op.drop_constraint("fk_invoices_payer", "invoices", type_="foreignkey")
    op.drop_constraint("fk_invoices_coverage", "invoices", type_="foreignkey")
    op.drop_column("invoices", "payer_id")
    op.drop_column("invoices", "coverage_id")
