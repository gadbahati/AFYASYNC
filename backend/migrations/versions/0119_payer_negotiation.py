"""payer negotiation workspace
Revision ID: 0119_payer_negotiation
Revises: 0118_denial_appeals
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision="0119_payer_negotiation"
down_revision="0118_denial_appeals"
branch_labels=None
depends_on=None

def upgrade():
    op.create_table(
        "payer_negotiation_cases",
        sa.Column("id",postgresql.UUID(as_uuid=True),primary_key=True),
        sa.Column("facility_id",postgresql.UUID(as_uuid=True),sa.ForeignKey("facilities.id",ondelete="CASCADE"),nullable=False,index=True),
        sa.Column("contract_id",postgresql.UUID(as_uuid=True),sa.ForeignKey("provider_network_contracts.id",ondelete="CASCADE"),nullable=False,index=True),
        sa.Column("case_number",sa.String(80),nullable=False,unique=True),
        sa.Column("status",sa.String(30),nullable=False,server_default="DRAFT",index=True),
        sa.Column("owner_id",postgresql.UUID(as_uuid=True),sa.ForeignKey("users.id",ondelete="RESTRICT")),
        sa.Column("due_at",sa.DateTime(timezone=True)),
        sa.Column("objective",sa.Text()),
        sa.Column("opening_position",postgresql.JSONB()),
        sa.Column("target_position",postgresql.JSONB()),
        sa.Column("evidence_snapshot",postgresql.JSONB()),
        sa.Column("proposed_terms",postgresql.JSONB()),
        sa.Column("accepted_terms",postgresql.JSONB()),
        sa.Column("notes",sa.Text()),
        sa.Column("created_at",sa.DateTime(timezone=True),server_default=sa.func.now(),nullable=False),
        sa.Column("updated_at",sa.DateTime(timezone=True),server_default=sa.func.now(),nullable=False),
        sa.Column("closed_at",sa.DateTime(timezone=True)),
    )
    op.create_index("ix_payer_negotiation_contract_status","payer_negotiation_cases","contract_id","status")
    op.create_table(
        "payer_negotiation_items",
        sa.Column("id",postgresql.UUID(as_uuid=True),primary_key=True),
        sa.Column("case_id",postgresql.UUID(as_uuid=True),sa.ForeignKey("payer_negotiation_cases.id",ondelete="CASCADE"),nullable=False,index=True),
        sa.Column("item_type",sa.String(40),nullable=False),
        sa.Column("title",sa.String(200),nullable=False),
        sa.Column("current_value",postgresql.JSONB()),
        sa.Column("requested_value",postgresql.JSONB()),
        sa.Column("rationale",sa.Text()),
        sa.Column("priority",sa.String(20),nullable=False,server_default="MEDIUM"),
        sa.Column("status",sa.String(25),nullable=False,server_default="PROPOSED",index=True),
        sa.Column("external_response",sa.Text()),
        sa.Column("created_at",sa.DateTime(timezone=True),server_default=sa.func.now(),nullable=False),
        sa.Column("updated_at",sa.DateTime(timezone=True),server_default=sa.func.now(),nullable=False),
    )
    op.create_table(
        "payer_negotiation_events",
        sa.Column("id",postgresql.UUID(as_uuid=True),primary_key=True),
        sa.Column("case_id",postgresql.UUID(as_uuid=True),sa.ForeignKey("payer_negotiation_cases.id",ondelete="CASCADE"),nullable=False,index=True),
        sa.Column("event_type",sa.String(50),nullable=False),
        sa.Column("from_status",sa.String(30)),
        sa.Column("to_status",sa.String(30)),
        sa.Column("actor_id",postgresql.UUID(as_uuid=True),sa.ForeignKey("users.id",ondelete="RESTRICT")),
        sa.Column("note",sa.Text()),
        sa.Column("metadata",postgresql.JSONB()),
        sa.Column("created_at",sa.DateTime(timezone=True),server_default=sa.func.now(),nullable=False),
    )
    op.create_index("ix_payer_negotiation_events_case_created","payer_negotiation_events","case_id","created_at")

def downgrade():
    op.drop_index("ix_payer_negotiation_events_case_created",table_name="payer_negotiation_events")
    op.drop_table("payer_negotiation_events")
    op.drop_table("payer_negotiation_items")
    op.drop_index("ix_payer_negotiation_contract_status",table_name="payer_negotiation_cases")
    op.drop_table("payer_negotiation_cases")
