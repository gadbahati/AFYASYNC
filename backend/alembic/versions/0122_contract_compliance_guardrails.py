"""contract compliance revenue guardrails

Revision ID: 0122_contract_compliance_guardrails
Revises: 0121_contract_operational_activation
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0122_contract_compliance_guardrails"
down_revision = "0121_contract_operational_activation"
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        "contract_compliance_guardrails",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("facility_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("facilities.id", ondelete="CASCADE"), nullable=False),
        sa.Column("contract_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("provider_network_contracts.id", ondelete="SET NULL"), nullable=True),
        sa.Column("claim_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("claims.id", ondelete="SET NULL"), nullable=True),
        sa.Column("payer_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("payers.id", ondelete="SET NULL"), nullable=True),
        sa.Column("guardrail_type", sa.String(50), nullable=False),
        sa.Column("severity", sa.String(20), nullable=False, server_default="MEDIUM"),
        sa.Column("status", sa.String(30), nullable=False, server_default="OPEN"),
        sa.Column("title", sa.String(220), nullable=False),
        sa.Column("expected_amount", sa.Numeric(14,2), nullable=False, server_default="0"),
        sa.Column("actual_amount", sa.Numeric(14,2), nullable=False, server_default="0"),
        sa.Column("amount_at_risk", sa.Numeric(14,2), nullable=False, server_default="0"),
        sa.Column("detail", sa.Text(), nullable=True),
        sa.Column("evidence", postgresql.JSONB(), nullable=True),
        sa.Column("assigned_to", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_contract_guardrail_facility","contract_compliance_guardrails",["facility_id"])
    op.create_index("ix_contract_guardrail_claim","contract_compliance_guardrails",["claim_id"])
    op.create_index("ix_contract_guardrail_contract","contract_compliance_guardrails",["contract_id"])
    op.create_index("ix_contract_guardrail_status","contract_compliance_guardrails",["status","severity"])
    op.create_index("ix_contract_guardrail_type","contract_compliance_guardrails",["guardrail_type"])

    op.create_table(
        "contract_compliance_guardrail_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("guardrail_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("contract_compliance_guardrails.id", ondelete="CASCADE"), nullable=False),
        sa.Column("event_type", sa.String(60), nullable=False),
        sa.Column("from_status", sa.String(30), nullable=True),
        sa.Column("to_status", sa.String(30), nullable=True),
        sa.Column("actor_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("metadata_json", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_contract_guardrail_events_guardrail","contract_compliance_guardrail_events",["guardrail_id","created_at"])

def downgrade():
    op.drop_table("contract_compliance_guardrail_events")
    op.drop_table("contract_compliance_guardrails")
