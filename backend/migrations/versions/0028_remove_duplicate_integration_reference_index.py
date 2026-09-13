"""remove the redundant duplicate integration external-reference index

Revision ID: 0028_remove_duplicate_integration_reference_index
Revises: 0027_merge_migration_heads
"""

from alembic import op
from sqlalchemy import inspect

revision = "0028_remove_duplicate_integration_reference_index"
down_revision = "0027_merge_migration_heads"
branch_labels = None
depends_on = None

_DUPLICATE_INDEX = "uq_integration_transaction_external_reference"


def upgrade() -> None:
    bind = op.get_bind()
    indexes = {index["name"] for index in inspect(bind).get_indexes("integration_transactions")}
    if _DUPLICATE_INDEX in indexes:
        op.drop_index(_DUPLICATE_INDEX, table_name="integration_transactions")


def downgrade() -> None:
    bind = op.get_bind()
    indexes = {index["name"] for index in inspect(bind).get_indexes("integration_transactions")}
    if _DUPLICATE_INDEX not in indexes:
        op.create_index(
            _DUPLICATE_INDEX,
            "integration_transactions",
            ["integration_id", "external_reference"],
            unique=True,
            postgresql_where="external_reference IS NOT NULL",
        )
