"""add integration callback uniqueness and retry indexes

Revision ID: 0022_integration_callback_integrity
Revises: 0021_invoice_claim_integrity
"""

from alembic import op

revision = "0022_integration_callback_integrity"
down_revision = "0021_invoice_claim_integrity"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "uq_integration_transaction_external_reference",
        "integration_transactions",
        ["integration_id", "external_reference"],
        unique=True,
        postgresql_where="external_reference IS NOT NULL",
    )
    op.create_index(
        "ix_integration_transactions_retry_queue",
        "integration_transactions",
        ["status", "attempt_count", "created_at"],
        unique=False,
        postgresql_where="status IN ('PENDING', 'RETRYING')",
    )


def downgrade() -> None:
    op.drop_index("ix_integration_transactions_retry_queue", table_name="integration_transactions")
    op.drop_index("uq_integration_transaction_external_reference", table_name="integration_transactions")
