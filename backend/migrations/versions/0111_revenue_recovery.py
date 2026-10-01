"""revenue recovery and settlement variance
Revision ID: 0111_revenue_recovery
Revises: 0110_claim_clearinghouse
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
revision="0111_revenue_recovery"
down_revision="0110_claim_clearinghouse"
branch_labels=None
depends_on=None
def upgrade():
    op.add_column("settlement_reconciliations",sa.Column("variance_type",sa.String(40),nullable=True))
    op.add_column("settlement_reconciliations",sa.Column("notes",sa.Text(),nullable=True))
    op.add_column("settlement_reconciliations",sa.Column("recovery_status",sa.String(30),nullable=False,server_default="OPEN"))
    op.create_index("ix_settlement_reconciliation_recovery","settlement_reconciliations",["status","recovery_status"])
    op.create_table(
      "revenue_recovery_cases",
      sa.Column("id",postgresql.UUID(as_uuid=True),primary_key=True),
      sa.Column("case_number",sa.String(90),unique=True,nullable=False),
      sa.Column("facility_id",postgresql.UUID(as_uuid=True),sa.ForeignKey("facilities.id",ondelete="RESTRICT"),nullable=False),
      sa.Column("payer_id",postgresql.UUID(as_uuid=True),sa.ForeignKey("payers.id",ondelete="RESTRICT")),
      sa.Column("claim_id",postgresql.UUID(as_uuid=True),sa.ForeignKey("claims.id",ondelete="SET NULL")),
      sa.Column("batch_id",postgresql.UUID(as_uuid=True),sa.ForeignKey("settlement_batches.id",ondelete="SET NULL")),
      sa.Column("reconciliation_id",postgresql.UUID(as_uuid=True),sa.ForeignKey("settlement_reconciliations.id",ondelete="SET NULL")),
      sa.Column("reason",sa.String(60),nullable=False),
      sa.Column("expected_amount",sa.Numeric(14,2),nullable=False,server_default="0"),
      sa.Column("recovered_amount",sa.Numeric(14,2),nullable=False,server_default="0"),
      sa.Column("outstanding_amount",sa.Numeric(14,2),nullable=False,server_default="0"),
      sa.Column("status",sa.String(30),nullable=False,server_default="OPEN"),
      sa.Column("priority",sa.String(20),nullable=False,server_default="NORMAL"),
      sa.Column("owner_id",postgresql.UUID(as_uuid=True),sa.ForeignKey("users.id",ondelete="SET NULL")),
      sa.Column("external_reference",sa.String(150)),
      sa.Column("notes",sa.Text()),
      sa.Column("created_at",sa.DateTime(timezone=True),server_default=sa.func.now(),nullable=False),
      sa.Column("updated_at",sa.DateTime(timezone=True),server_default=sa.func.now(),nullable=False),
    )
    op.create_index("ix_recovery_cases_facility_status","revenue_recovery_cases",["facility_id","status"])
    op.create_index("ix_recovery_cases_payer_status","revenue_recovery_cases",["payer_id","status"])
    op.create_index("ix_recovery_cases_priority","revenue_recovery_cases",["priority","status"])
def downgrade():
    op.drop_index("ix_recovery_cases_priority",table_name="revenue_recovery_cases")
    op.drop_index("ix_recovery_cases_payer_status",table_name="revenue_recovery_cases")
    op.drop_index("ix_recovery_cases_facility_status",table_name="revenue_recovery_cases")
    op.drop_table("revenue_recovery_cases")
    op.drop_index("ix_settlement_reconciliation_recovery",table_name="settlement_reconciliations")
    op.drop_column("settlement_reconciliations","recovery_status")
    op.drop_column("settlement_reconciliations","notes")
    op.drop_column("settlement_reconciliations","variance_type")
