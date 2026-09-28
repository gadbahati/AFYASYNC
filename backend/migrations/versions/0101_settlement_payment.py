"""settlement and provider payment engine

Revision ID: 0101_settlement_payment
Revises: 0100_claim_adjudication
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
revision="0101_settlement_payment"
down_revision="0100_claim_adjudication"
branch_labels=None
depends_on=None

def upgrade():
    op.create_table(
        "settlement_obligations",
        sa.Column("id",postgresql.UUID(as_uuid=True),primary_key=True),
        sa.Column("obligation_number",sa.String(80),nullable=False,unique=True),
        sa.Column("claim_id",postgresql.UUID(as_uuid=True),sa.ForeignKey("claims.id",ondelete="RESTRICT"),nullable=False,unique=True),
        sa.Column("facility_id",postgresql.UUID(as_uuid=True),sa.ForeignKey("facilities.id",ondelete="RESTRICT"),nullable=False),
        sa.Column("payer_id",postgresql.UUID(as_uuid=True),sa.ForeignKey("payers.id",ondelete="RESTRICT"),nullable=False),
        sa.Column("submitted_amount",sa.Numeric(14,2),nullable=False),
        sa.Column("payable_amount",sa.Numeric(14,2),nullable=False),
        sa.Column("patient_amount",sa.Numeric(14,2),nullable=False),
        sa.Column("status",sa.String(30),nullable=False,server_default="READY"),
        sa.Column("due_at",sa.DateTime(timezone=True)),
        sa.Column("created_at",sa.DateTime(timezone=True),server_default=sa.func.now()),
    )
    for n in ["claim_id","facility_id","payer_id","status"]: op.create_index("ix_settlement_obligations_"+n,"settlement_obligations",[n])
    op.create_table(
        "settlement_batches",
        sa.Column("id",postgresql.UUID(as_uuid=True),primary_key=True),
        sa.Column("batch_number",sa.String(80),nullable=False,unique=True),
        sa.Column("facility_id",postgresql.UUID(as_uuid=True),sa.ForeignKey("facilities.id",ondelete="RESTRICT"),nullable=False),
        sa.Column("payer_id",postgresql.UUID(as_uuid=True),sa.ForeignKey("payers.id",ondelete="RESTRICT"),nullable=False),
        sa.Column("total_amount",sa.Numeric(14,2),nullable=False,server_default="0"),
        sa.Column("status",sa.String(30),nullable=False,server_default="DRAFT"),
        sa.Column("created_by",postgresql.UUID(as_uuid=True),sa.ForeignKey("users.id",ondelete="SET NULL")),
        sa.Column("created_at",sa.DateTime(timezone=True),server_default=sa.func.now()),
        sa.Column("submitted_at",sa.DateTime(timezone=True)),
        sa.Column("settled_at",sa.DateTime(timezone=True)),
    )
    for n in ["facility_id","payer_id","status"]: op.create_index("ix_settlement_batches_"+n,"settlement_batches",[n])
    op.create_table(
        "provider_payments",
        sa.Column("id",postgresql.UUID(as_uuid=True),primary_key=True),
        sa.Column("payment_reference",sa.String(100),nullable=False,unique=True),
        sa.Column("batch_id",postgresql.UUID(as_uuid=True),sa.ForeignKey("settlement_batches.id",ondelete="RESTRICT"),nullable=False),
        sa.Column("obligation_id",postgresql.UUID(as_uuid=True),sa.ForeignKey("settlement_obligations.id",ondelete="RESTRICT"),nullable=False,unique=True),
        sa.Column("facility_id",postgresql.UUID(as_uuid=True),sa.ForeignKey("facilities.id",ondelete="RESTRICT"),nullable=False),
        sa.Column("payer_id",postgresql.UUID(as_uuid=True),sa.ForeignKey("payers.id",ondelete="RESTRICT"),nullable=False),
        sa.Column("amount",sa.Numeric(14,2),nullable=False),
        sa.Column("method",sa.String(40),nullable=False),
        sa.Column("external_reference",sa.String(150)),
        sa.Column("status",sa.String(30),nullable=False,server_default="RECORDED"),
        sa.Column("created_at",sa.DateTime(timezone=True),server_default=sa.func.now()),
        sa.Column("confirmed_at",sa.DateTime(timezone=True)),
    )
    for n in ["batch_id","obligation_id","facility_id","payer_id","status"]: op.create_index("ix_provider_payments_"+n,"provider_payments",[n])
    op.create_table(
        "settlement_reconciliations",
        sa.Column("id",postgresql.UUID(as_uuid=True),primary_key=True),
        sa.Column("batch_id",postgresql.UUID(as_uuid=True),sa.ForeignKey("settlement_batches.id",ondelete="RESTRICT"),nullable=False),
        sa.Column("expected_amount",sa.Numeric(14,2),nullable=False),
        sa.Column("received_amount",sa.Numeric(14,2),nullable=False),
        sa.Column("difference",sa.Numeric(14,2),nullable=False),
        sa.Column("status",sa.String(30),nullable=False,server_default="PENDING"),
        sa.Column("reconciled_by",postgresql.UUID(as_uuid=True),sa.ForeignKey("users.id",ondelete="SET NULL")),
        sa.Column("reconciled_at",sa.DateTime(timezone=True)),
    )
    op.create_index("ix_settlement_reconciliations_batch_id","settlement_reconciliations",["batch_id"])
    op.create_table(
        "settlement_ledger_entries",
        sa.Column("id",postgresql.UUID(as_uuid=True),primary_key=True),
        sa.Column("batch_id",postgresql.UUID(as_uuid=True),sa.ForeignKey("settlement_batches.id",ondelete="RESTRICT"),nullable=False),
        sa.Column("obligation_id",postgresql.UUID(as_uuid=True),sa.ForeignKey("settlement_obligations.id",ondelete="SET NULL")),
        sa.Column("entry_type",sa.String(40),nullable=False),
        sa.Column("debit_amount",sa.Numeric(14,2),nullable=False,server_default="0"),
        sa.Column("credit_amount",sa.Numeric(14,2),nullable=False,server_default="0"),
        sa.Column("currency",sa.String(3),nullable=False,server_default="KES"),
        sa.Column("reference",sa.String(150),nullable=False),
        sa.Column("created_at",sa.DateTime(timezone=True),server_default=sa.func.now()),
    )
    op.create_index("ix_settlement_ledger_entries_batch_id","settlement_ledger_entries",["batch_id"])
    op.create_index("ix_settlement_ledger_entries_obligation_id","settlement_ledger_entries",["obligation_id"])
    op.create_index("ix_settlement_ledger_entries_reference","settlement_ledger_entries",["reference"])

def downgrade():
    for n in ["reference","obligation_id","batch_id"]: op.drop_index("ix_settlement_ledger_entries_"+n,table_name="settlement_ledger_entries")
    op.drop_table("settlement_ledger_entries")
    op.drop_index("ix_settlement_reconciliations_batch_id",table_name="settlement_reconciliations")
    op.drop_table("settlement_reconciliations")
    for n in ["status","payer_id","facility_id","obligation_id","batch_id"]: op.drop_index("ix_provider_payments_"+n,table_name="provider_payments")
    op.drop_table("provider_payments")
    for n in ["status","payer_id","facility_id"]: op.drop_index("ix_settlement_batches_"+n,table_name="settlement_batches")
    op.drop_table("settlement_batches")
    for n in ["status","payer_id","facility_id","claim_id"]: op.drop_index("ix_settlement_obligations_"+n,table_name="settlement_obligations")
    op.drop_table("settlement_obligations")
