"""contract operational activation
Revision ID: 0121_contract_operational_activation
Revises: 0120_negotiation_contract_execution
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision="0121_contract_operational_activation"
down_revision="0120_negotiation_contract_execution"
branch_labels=None
depends_on=None

def upgrade():
    op.add_column("provider_network_contracts",sa.Column("activation_status",sa.String(30),nullable=False,server_default="NOT_ACTIVATED"))
    op.add_column("provider_network_contracts",sa.Column("activated_at",sa.DateTime(timezone=True)))
    op.add_column("provider_network_contracts",sa.Column("activation_summary",postgresql.JSONB()))
    op.create_index("ix_provider_network_contract_activation","provider_network_contracts",["activation_status"])
    op.create_table(
        "contract_activation_events",
        sa.Column("id",postgresql.UUID(as_uuid=True),primary_key=True),
        sa.Column("facility_id",postgresql.UUID(as_uuid=True),sa.ForeignKey("facilities.id",ondelete="CASCADE"),nullable=False,index=True),
        sa.Column("contract_id",postgresql.UUID(as_uuid=True),sa.ForeignKey("provider_network_contracts.id",ondelete="CASCADE"),nullable=False,index=True),
        sa.Column("event_type",sa.String(60),nullable=False),
        sa.Column("status",sa.String(30),nullable=False),
        sa.Column("actor_id",postgresql.UUID(as_uuid=True),sa.ForeignKey("users.id",ondelete="RESTRICT")),
        sa.Column("details",postgresql.JSONB()),
        sa.Column("created_at",sa.DateTime(timezone=True),server_default=sa.func.now(),nullable=False),
    )
    op.create_index("ix_contract_activation_events_contract_created","contract_activation_events",["contract_id","created_at"])

def downgrade():
    op.drop_index("ix_contract_activation_events_contract_created",table_name="contract_activation_events")
    op.drop_table("contract_activation_events")
    op.drop_index("ix_provider_network_contract_activation",table_name="provider_network_contracts")
    op.drop_column("provider_network_contracts","activation_summary")
    op.drop_column("provider_network_contracts","activated_at")
    op.drop_column("provider_network_contracts","activation_status")
