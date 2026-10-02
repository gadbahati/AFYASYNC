"""negotiation contract execution
Revision ID: 0120_negotiation_contract_execution
Revises: 0119_payer_negotiation
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
revision="0120_negotiation_contract_execution"
down_revision="0119_payer_negotiation"
branch_labels=None
depends_on=None
def upgrade():
    op.add_column("provider_network_contracts",sa.Column("execution_status",sa.String(30),nullable=False,server_default="NOT_STARTED"))
    op.add_column("provider_network_contracts",sa.Column("executed_at",sa.DateTime(timezone=True)))
    op.add_column("provider_network_contracts",sa.Column("execution_reference",sa.String(120)))
    op.add_column("provider_network_contracts",sa.Column("executed_terms",postgresql.JSONB()))
    op.add_column("provider_network_contracts",sa.Column("execution_notes",sa.Text()))
    op.create_index("ix_provider_network_contract_execution","provider_network_contracts","execution_status")
    op.create_table("contract_execution_approvals",
        sa.Column("id",postgresql.UUID(as_uuid=True),primary_key=True),
        sa.Column("facility_id",postgresql.UUID(as_uuid=True),sa.ForeignKey("facilities.id",ondelete="CASCADE"),nullable=False,index=True),
        sa.Column("contract_id",postgresql.UUID(as_uuid=True),sa.ForeignKey("provider_network_contracts.id",ondelete="CASCADE"),nullable=False,index=True),
        sa.Column("negotiation_case_id",postgresql.UUID(as_uuid=True),sa.ForeignKey("payer_negotiation_cases.id",ondelete="SET NULL")),
        sa.Column("status",sa.String(25),nullable=False,server_default="PENDING",index=True),
        sa.Column("requested_by",postgresql.UUID(as_uuid=True),sa.ForeignKey("users.id",ondelete="RESTRICT")),
        sa.Column("reviewed_by",postgresql.UUID(as_uuid=True),sa.ForeignKey("users.id",ondelete="RESTRICT")),
        sa.Column("requested_at",sa.DateTime(timezone=True),server_default=sa.func.now(),nullable=False),
        sa.Column("reviewed_at",sa.DateTime(timezone=True)),
        sa.Column("requested_terms",postgresql.JSONB()),
        sa.Column("review_notes",sa.Text())
    )
    op.create_table("contract_execution_events",
        sa.Column("id",postgresql.UUID(as_uuid=True),primary_key=True),
        sa.Column("contract_id",postgresql.UUID(as_uuid=True),sa.ForeignKey("provider_network_contracts.id",ondelete="CASCADE"),nullable=False,index=True),
        sa.Column("approval_id",postgresql.UUID(as_uuid=True),sa.ForeignKey("contract_execution_approvals.id",ondelete="SET NULL")),
        sa.Column("event_type",sa.String(50),nullable=False),
        sa.Column("actor_id",postgresql.UUID(as_uuid=True),sa.ForeignKey("users.id",ondelete="RESTRICT")),
        sa.Column("notes",sa.Text()),
        sa.Column("metadata",postgresql.JSONB()),
        sa.Column("created_at",sa.DateTime(timezone=True),server_default=sa.func.now(),nullable=False)
    )
    op.create_index("ix_contract_execution_events_contract_created","contract_execution_events",["contract_id","created_at"])
def downgrade():
    op.drop_index("ix_contract_execution_events_contract_created",table_name="contract_execution_events")
    op.drop_table("contract_execution_events")
    op.drop_table("contract_execution_approvals")
    op.drop_index("ix_provider_network_contract_execution",table_name="provider_network_contracts")
    for c in ["execution_notes","executed_terms","execution_reference","executed_at","execution_status"]:
        op.drop_column("provider_network_contracts",c)
