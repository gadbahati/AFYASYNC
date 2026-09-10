"""add integration engine tables

Revision ID: 0012_integrations
Revises: 0011_permissions
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0012_integrations"
down_revision = "0011_permissions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table("integrations",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.String(150), nullable=False), sa.Column("integration_type", sa.String(60), nullable=False),
        sa.Column("provider", sa.String(120), nullable=False), sa.Column("status", sa.String(30), nullable=False, server_default="ACTIVE"),
        sa.Column("configuration", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")), sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"))
    op.create_index("ix_integrations_status", "integrations", ["status"])

    op.create_table("integration_transactions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column("integration_id", postgresql.UUID(as_uuid=True), nullable=False), sa.Column("transaction_id", sa.String(120), nullable=False),
        sa.Column("entity_type", sa.String(80), nullable=False), sa.Column("entity_id", postgresql.UUID(as_uuid=True)),
        sa.Column("direction", sa.String(20), nullable=False), sa.Column("request_reference", sa.String(150)), sa.Column("external_reference", sa.String(150)),
        sa.Column("status", sa.String(30), nullable=False, server_default="PENDING"), sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_attempt_at", sa.DateTime(timezone=True)), sa.Column("response_code", sa.String(80)),
        sa.Column("response_data", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")), sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["integration_id"], ["integrations.id"], ondelete="RESTRICT"), sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("integration_id", "transaction_id", name="uq_integration_transaction"))
    op.create_index("ix_integration_transactions_integration_id", "integration_transactions", ["integration_id"])
    op.create_index("ix_integration_transactions_status", "integration_transactions", ["status"])


def downgrade() -> None:
    op.drop_index("ix_integration_transactions_status", table_name="integration_transactions")
    op.drop_index("ix_integration_transactions_integration_id", table_name="integration_transactions")
    op.drop_table("integration_transactions")
    op.drop_index("ix_integrations_status", table_name="integrations")
    op.drop_table("integrations")
