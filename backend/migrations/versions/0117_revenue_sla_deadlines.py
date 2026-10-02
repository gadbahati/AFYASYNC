"""Complete payer SLA deadline tracking
Revision ID: 0117_revenue_sla_deadlines
Revises: 0116_payer_sla_denial_ops
"""
from alembic import op
import sqlalchemy as sa
revision="0117_revenue_sla_deadlines"; down_revision="0116_payer_sla_denial_ops"; branch_labels=None; depends_on=None
def upgrade():
    op.add_column("revenue_resolution_cases",sa.Column("denial_response_due_at",sa.DateTime(timezone=True),nullable=True))
    op.add_column("revenue_resolution_cases",sa.Column("escalation_due_at",sa.DateTime(timezone=True),nullable=True))
    op.create_index("ix_revenue_resolution_response_sla","revenue_resolution_cases",["facility_id","denial_response_due_at","first_response_at"])
    op.create_index("ix_revenue_resolution_escalation_sla","revenue_resolution_cases",["facility_id","escalation_due_at","escalation_level"])
def downgrade():
    op.drop_index("ix_revenue_resolution_escalation_sla",table_name="revenue_resolution_cases")
    op.drop_index("ix_revenue_resolution_response_sla",table_name="revenue_resolution_cases")
    op.drop_column("revenue_resolution_cases","escalation_due_at")
    op.drop_column("revenue_resolution_cases","denial_response_due_at")
