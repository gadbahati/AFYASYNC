"""Phase 64 payer SLA and denial operations
Revision ID: 0116_payer_sla_denial_ops
Revises: 0115_revenue_resolution
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
revision="0116_payer_sla_denial_ops"; down_revision="0115_revenue_resolution"; branch_labels=None; depends_on=None
def upgrade():
    op.create_table("payer_sla_policies",
        sa.Column("id",postgresql.UUID(as_uuid=True),primary_key=True),
        sa.Column("payer_id",postgresql.UUID(as_uuid=True),sa.ForeignKey("payers.id",ondelete="CASCADE"),nullable=False),
        sa.Column("facility_id",postgresql.UUID(as_uuid=True),sa.ForeignKey("facilities.id",ondelete="CASCADE"),nullable=False),
        sa.Column("denial_response_hours",sa.Integer(),nullable=False,server_default="48"),
        sa.Column("resolution_hours",sa.Integer(),nullable=False,server_default="168"),
        sa.Column("appeal_hours",sa.Integer(),nullable=False,server_default="120"),
        sa.Column("escalation_hours",sa.Integer(),nullable=False,server_default="24"),
        sa.Column("active",sa.Boolean(),nullable=False,server_default=sa.true()),
        sa.Column("notes",sa.Text()),sa.Column("created_at",sa.DateTime(timezone=True),server_default=sa.func.now(),nullable=False),
        sa.Column("updated_at",sa.DateTime(timezone=True),server_default=sa.func.now(),nullable=False),
        sa.UniqueConstraint("facility_id","payer_id",name="uq_payer_sla_policy_facility_payer"))
    op.create_index("ix_payer_sla_policies_facility","payer_sla_policies",["facility_id","active"])
    op.create_index("ix_payer_sla_policies_payer","payer_sla_policies",["payer_id","active"])
    for name,col in [("sla_due_at",sa.DateTime(timezone=True)),("first_response_at",sa.DateTime(timezone=True)),("appeal_due_at",sa.DateTime(timezone=True)),("escalation_level",sa.Integer()),("sla_status",sa.String(20)),("sla_breached_at",sa.DateTime(timezone=True))]:
        kwargs={"nullable":False,"server_default":"0"} if name=="escalation_level" else {"nullable":False,"server_default":"ON_TRACK"} if name=="sla_status" else {"nullable":True}
        op.add_column("revenue_resolution_cases",sa.Column(name,col,**kwargs))
    op.create_index("ix_revenue_resolution_sla","revenue_resolution_cases",["facility_id","sla_status","sla_due_at"])
    op.create_table("revenue_resolution_sla_events",
        sa.Column("id",postgresql.UUID(as_uuid=True),primary_key=True),
        sa.Column("case_id",postgresql.UUID(as_uuid=True),sa.ForeignKey("revenue_resolution_cases.id",ondelete="CASCADE"),nullable=False),
        sa.Column("event_type",sa.String(60),nullable=False),sa.Column("from_level",sa.Integer()),sa.Column("to_level",sa.Integer()),
        sa.Column("note",sa.Text()),sa.Column("actor_id",postgresql.UUID(as_uuid=True),sa.ForeignKey("users.id",ondelete="SET NULL")),
        sa.Column("created_at",sa.DateTime(timezone=True),server_default=sa.func.now(),nullable=False))
    op.create_index("ix_revenue_resolution_sla_events_case","revenue_resolution_sla_events",["case_id","created_at"])
def downgrade():
    op.drop_index("ix_revenue_resolution_sla_events_case",table_name="revenue_resolution_sla_events"); op.drop_table("revenue_resolution_sla_events")
    op.drop_index("ix_revenue_resolution_sla",table_name="revenue_resolution_cases")
    for c in ["sla_breached_at","sla_status","escalation_level","appeal_due_at","first_response_at","sla_due_at"]: op.drop_column("revenue_resolution_cases",c)
    op.drop_index("ix_payer_sla_policies_payer",table_name="payer_sla_policies"); op.drop_index("ix_payer_sla_policies_facility",table_name="payer_sla_policies"); op.drop_table("payer_sla_policies")
