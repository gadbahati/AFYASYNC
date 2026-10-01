"""provider contracting and empanelment lifecycle
Revision ID: 0109_provider_contracting
Revises: 0108_benefit_engine
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0109_provider_contracting"
down_revision = "0108_benefit_engine"
branch_labels = None
depends_on = None

def upgrade():
    op.add_column("provider_network_memberships", sa.Column("license_verified_at", sa.DateTime(timezone=True)))
    op.add_column("provider_network_memberships", sa.Column("credential_verified_at", sa.DateTime(timezone=True)))
    op.add_column("provider_network_memberships", sa.Column("service_verified_at", sa.DateTime(timezone=True)))
    op.add_column("provider_network_memberships", sa.Column("verification_notes", sa.Text()))
    op.add_column("provider_network_contracts", sa.Column("tariff_negotiated_at", sa.DateTime(timezone=True)))
    op.add_column("provider_network_contracts", sa.Column("accepted_at", sa.DateTime(timezone=True)))
    op.add_column("provider_network_contracts", sa.Column("accepted_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="RESTRICT")))
    op.add_column("provider_network_contracts", sa.Column("renewal_due_at", sa.DateTime(timezone=True)))
    op.add_column("provider_network_contracts", sa.Column("suspension_reason", sa.Text()))
    op.create_table(
        "provider_contract_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("contract_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("provider_network_contracts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("event_type", sa.String(50), nullable=False),
        sa.Column("from_status", sa.String(30)),
        sa.Column("to_status", sa.String(30)),
        sa.Column("actor_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="RESTRICT")),
        sa.Column("notes", sa.Text()),
        sa.Column("metadata", postgresql.JSONB()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_provider_contract_events_contract", "provider_contract_events", ["contract_id", "created_at"])
    op.create_index("ix_provider_contract_events_type", "provider_contract_events", ["event_type"])

def downgrade():
    op.drop_index("ix_provider_contract_events_type", table_name="provider_contract_events")
    op.drop_index("ix_provider_contract_events_contract", table_name="provider_contract_events")
    op.drop_table("provider_contract_events")
    op.drop_column("provider_network_contracts", "suspension_reason")
    op.drop_column("provider_network_contracts", "renewal_due_at")
    op.drop_column("provider_network_contracts", "accepted_by")
    op.drop_column("provider_network_contracts", "accepted_at")
    op.drop_column("provider_network_contracts", "tariff_negotiated_at")
    op.drop_column("provider_network_memberships", "verification_notes")
    op.drop_column("provider_network_memberships", "service_verified_at")
    op.drop_column("provider_network_memberships", "credential_verified_at")
    op.drop_column("provider_network_memberships", "license_verified_at")
