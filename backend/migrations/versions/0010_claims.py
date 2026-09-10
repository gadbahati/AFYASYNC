"""add claims and reconciliation tables

Revision ID: 0010
Revises: 0009
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None


def _uuid(name: str) -> sa.Column:
    return sa.Column(name, postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text("gen_random_uuid()"))


def upgrade() -> None:
    op.create_table("claims", _uuid("id"),
        sa.Column("claim_id", sa.String(70), nullable=False), sa.Column("invoice_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("encounter_id", postgresql.UUID(as_uuid=True), nullable=False), sa.Column("patient_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("payer_id", postgresql.UUID(as_uuid=True), nullable=False), sa.Column("claim_amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("approved_amount", sa.Numeric(14, 2), nullable=False, server_default="0"), sa.Column("paid_amount", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("status", sa.String(30), nullable=False, server_default="DRAFT"), sa.Column("submitted_at", sa.DateTime(timezone=True)),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["invoice_id"], ["invoices.id"], ondelete="RESTRICT"), sa.ForeignKeyConstraint(["encounter_id"], ["encounters.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["patient_id"], ["persons.id"], ondelete="RESTRICT"), sa.ForeignKeyConstraint(["payer_id"], ["payers.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"), sa.UniqueConstraint("claim_id"))
    for name, col in [("ix_claims_claim_id", "claim_id"), ("ix_claims_invoice_id", "invoice_id"), ("ix_claims_encounter_id", "encounter_id"), ("ix_claims_patient_id", "patient_id"), ("ix_claims_payer_id", "payer_id"), ("ix_claims_status", "status")]:
        op.create_index(name, "claims", [col])
    op.create_table("claim_items", _uuid("id"),
        sa.Column("claim_id", postgresql.UUID(as_uuid=True), nullable=False), sa.Column("charge_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("service_code", sa.String(80), nullable=False), sa.Column("quantity", sa.Numeric(12, 2), nullable=False), sa.Column("amount", sa.Numeric(14, 2), nullable=False),
        sa.ForeignKeyConstraint(["claim_id"], ["claims.id"], ondelete="RESTRICT"), sa.ForeignKeyConstraint(["charge_id"], ["charges.id"], ondelete="RESTRICT"), sa.PrimaryKeyConstraint("id"))
    op.create_index("ix_claim_items_claim_id", "claim_items", ["claim_id"])
    op.create_table("claim_responses", _uuid("id"),
        sa.Column("claim_id", postgresql.UUID(as_uuid=True), nullable=False), sa.Column("external_reference", sa.String(150)), sa.Column("status", sa.String(40), nullable=False),
        sa.Column("response_code", sa.String(80)), sa.Column("response_message", sa.String(500)), sa.Column("received_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["claim_id"], ["claims.id"], ondelete="RESTRICT"), sa.PrimaryKeyConstraint("id"))
    op.create_index("ix_claim_responses_claim_id", "claim_responses", ["claim_id"])
    op.create_table("reconciliations", _uuid("id"),
        sa.Column("claim_id", postgresql.UUID(as_uuid=True), nullable=False), sa.Column("expected_amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("received_amount", sa.Numeric(14, 2), nullable=False), sa.Column("difference", sa.Numeric(14, 2), nullable=False), sa.Column("status", sa.String(30), nullable=False, server_default="PENDING"),
        sa.Column("reconciled_by", postgresql.UUID(as_uuid=True)), sa.Column("reconciled_at", sa.DateTime(timezone=True)),
        sa.ForeignKeyConstraint(["claim_id"], ["claims.id"], ondelete="RESTRICT"), sa.ForeignKeyConstraint(["reconciled_by"], ["staff.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"), sa.UniqueConstraint("claim_id", name="uq_reconciliation_claim"))
    op.create_index("ix_reconciliations_claim_id", "reconciliations", ["claim_id"])


def downgrade() -> None:
    op.drop_index("ix_reconciliations_claim_id", table_name="reconciliations")
    op.drop_table("reconciliations")
    op.drop_index("ix_claim_responses_claim_id", table_name="claim_responses")
    op.drop_table("claim_responses")
    op.drop_index("ix_claim_items_claim_id", table_name="claim_items")
    op.drop_table("claim_items")
    for name in ["ix_claims_status", "ix_claims_payer_id", "ix_claims_patient_id", "ix_claims_encounter_id", "ix_claims_invoice_id", "ix_claims_claim_id"]:
        op.drop_index(name, table_name="claims")
    op.drop_table("claims")
