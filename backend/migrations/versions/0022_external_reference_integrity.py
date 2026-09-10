"""enforce external reference uniqueness for payment/integration callbacks

Revision ID: 0022_external_reference_integrity
Revises: 0021_invoice_claim_integrity
"""

from alembic import op
import sqlalchemy as sa

revision = "0022_external_reference_integrity"
down_revision = "0021_invoice_claim_integrity"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "uq_payments_facility_external_reference",
        "payments",
        ["facility_id", "external_reference"],
        unique=True,
        postgresql_where=sa.text("external_reference IS NOT NULL"),
    )
    op.create_index(
        "uq_integration_external_reference",
        "integration_transactions",
        ["integration_id", "external_reference"],
        unique=True,
        postgresql_where=sa.text("external_reference IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("uq_integration_external_reference", table_name="integration_transactions")
    op.drop_index("uq_payments_facility_external_reference", table_name="payments")
