"""payer-agnostic patient financing wallet
Revision ID: 0103_financing_wallet
Revises: 0102_fraud_integrity_cases
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0103_financing_wallet"
down_revision = "0102_fraud_integrity_cases"
branch_labels = None
depends_on = None

def upgrade():
    op.create_table("financing_wallets",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("person_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("persons.id", ondelete="RESTRICT"), nullable=False, unique=True),
        sa.Column("currency", sa.String(3), nullable=False, server_default="KES"),
        sa.Column("status", sa.String(30), nullable=False, server_default="ACTIVE"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_financing_wallets_person_id","financing_wallets",["person_id"])
    op.create_index("ix_financing_wallets_status","financing_wallets",["status"])

    op.create_table("financing_wallet_transactions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("wallet_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("financing_wallets.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("person_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("persons.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("facility_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("facilities.id", ondelete="SET NULL")),
        sa.Column("invoice_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("invoices.id", ondelete="SET NULL")),
        sa.Column("payer_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("payers.id", ondelete="SET NULL")),
        sa.Column("transaction_type", sa.String(40), nullable=False),
        sa.Column("direction", sa.String(10), nullable=False),
        sa.Column("amount", sa.Numeric(14,2), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False, server_default="KES"),
        sa.Column("reference", sa.String(150), nullable=False),
        sa.Column("description", sa.String(500)),
        sa.Column("source_type", sa.String(50), nullable=False, server_default="MANUAL"),
        sa.Column("source_id", sa.String(150)),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("wallet_id","reference",name="uq_financing_wallet_tx_reference"),
    )
    for n in ["wallet_id","person_id","facility_id","invoice_id","payer_id","transaction_type","created_at"]:
        op.create_index("ix_financing_wallet_transactions_"+n,"financing_wallet_transactions",[n])
    op.create_index("ix_financing_wallet_tx_wallet_created","financing_wallet_transactions",["wallet_id","created_at"])

def downgrade():
    op.drop_index("ix_financing_wallet_tx_wallet_created", table_name="financing_wallet_transactions")
    for n in ["created_at","transaction_type","payer_id","invoice_id","facility_id","person_id","wallet_id"]:
        op.drop_index("ix_financing_wallet_transactions_"+n, table_name="financing_wallet_transactions")
    op.drop_table("financing_wallet_transactions")
    op.drop_index("ix_financing_wallets_status", table_name="financing_wallets")
    op.drop_index("ix_financing_wallets_person_id", table_name="financing_wallets")
    op.drop_table("financing_wallets")
