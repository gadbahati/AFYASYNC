"""Denial appeal operations
Revision ID: 0118_denial_appeals
Revises: 0117_revenue_sla_deadlines
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
revision="0118_denial_appeals"; down_revision="0117_revenue_sla_deadlines"; branch_labels=None; depends_on=None
def upgrade():
    op.create_table("denial_appeals",
        sa.Column("id",postgresql.UUID(as_uuid=True),primary_key=True),
        sa.Column("facility_id",postgresql.UUID(as_uuid=True),sa.ForeignKey("facilities.id",ondelete="RESTRICT"),nullable=False),
        sa.Column("clearinghouse_case_id",postgresql.UUID(as_uuid=True),sa.ForeignKey("clearinghouse_cases.id",ondelete="CASCADE"),nullable=False),
        sa.Column("resolution_case_id",postgresql.UUID(as_uuid=True),sa.ForeignKey("revenue_resolution_cases.id",ondelete="SET NULL")),
        sa.Column("appeal_number",sa.String(90),nullable=False,unique=True),
        sa.Column("status",sa.String(30),nullable=False,server_default="DRAFT"),
        sa.Column("assigned_to",postgresql.UUID(as_uuid=True),sa.ForeignKey("users.id",ondelete="SET NULL")),
        sa.Column("due_at",sa.DateTime(timezone=True)),
        sa.Column("submitted_at",sa.DateTime(timezone=True)),
        sa.Column("resolved_at",sa.DateTime(timezone=True)),
        sa.Column("external_reference",sa.String(180)),
        sa.Column("grounds",sa.Text()),
        sa.Column("evidence_checklist",postgresql.JSONB()),
        sa.Column("submission_notes",sa.Text()),
        sa.Column("outcome",sa.String(40)),
        sa.Column("outcome_notes",sa.Text()),
        sa.Column("created_at",sa.DateTime(timezone=True),server_default=sa.func.now(),nullable=False),
        sa.Column("updated_at",sa.DateTime(timezone=True),server_default=sa.func.now(),nullable=False))
    op.create_index("ix_denial_appeals_facility_status","denial_appeals",["facility_id","status"])
    op.create_index("ix_denial_appeals_case","denial_appeals",["clearinghouse_case_id"])
    op.create_index("ix_denial_appeals_due","denial_appeals",["facility_id","due_at","status"])
    op.create_table("denial_appeal_events",
        sa.Column("id",postgresql.UUID(as_uuid=True),primary_key=True),
        sa.Column("appeal_id",postgresql.UUID(as_uuid=True),sa.ForeignKey("denial_appeals.id",ondelete="CASCADE"),nullable=False),
        sa.Column("event_type",sa.String(50),nullable=False),
        sa.Column("from_status",sa.String(30)),
        sa.Column("to_status",sa.String(30)),
        sa.Column("actor_id",postgresql.UUID(as_uuid=True),sa.ForeignKey("users.id",ondelete="SET NULL")),
        sa.Column("note",sa.Text()),
        sa.Column("created_at",sa.DateTime(timezone=True),server_default=sa.func.now(),nullable=False))
    op.create_index("ix_denial_appeal_events_appeal","denial_appeal_events",["appeal_id","created_at"])
def downgrade():
    op.drop_index("ix_denial_appeal_events_appeal",table_name="denial_appeal_events");op.drop_table("denial_appeal_events")
    op.drop_index("ix_denial_appeals_due",table_name="denial_appeals");op.drop_index("ix_denial_appeals_case",table_name="denial_appeals");op.drop_index("ix_denial_appeals_facility_status",table_name="denial_appeals");op.drop_table("denial_appeals")
