"""revenue anomaly and leakage investigation
Revision ID: 0113_revenue_anomalies
Revises: 0112_recovery_case_updates_repair
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0113_revenue_anomalies"
down_revision = "0112_recovery_case_updates_repair"
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        "revenue_anomaly_cases",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("case_number", sa.String(90), unique=True, nullable=False),
        sa.Column("facility_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("facilities.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("anomaly_type", sa.String(60), nullable=False),
        sa.Column("severity", sa.String(20), nullable=False, server_default="MEDIUM"),
        sa.Column("risk_score", sa.Integer(), nullable=False, server_default="50"),
        sa.Column("status", sa.String(30), nullable=False, server_default="OPEN"),
        sa.Column("claim_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("claims.id", ondelete="SET NULL")),
        sa.Column("invoice_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("invoices.id", ondelete="SET NULL")),
        sa.Column("patient_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("persons.id", ondelete="SET NULL")),
        sa.Column("payer_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("payers.id", ondelete="SET NULL")),
        sa.Column("recovery_case_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("revenue_recovery_cases.id", ondelete="SET NULL")),
        sa.Column("amount_at_risk", sa.Numeric(14,2), nullable=False, server_default="0"),
        sa.Column("fingerprint", sa.String(180), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("evidence", postgresql.JSONB()),
        sa.Column("notes", sa.Text()),
        sa.Column("assigned_to", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_revenue_anomaly_cases_facility_status", "revenue_anomaly_cases", ["facility_id","status"])
    op.create_index("ix_revenue_anomaly_cases_risk", "revenue_anomaly_cases", ["facility_id","risk_score"])
    op.create_index("ix_revenue_anomaly_cases_fingerprint", "revenue_anomaly_cases", ["fingerprint"])
    op.create_table(
        "revenue_anomaly_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("case_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("revenue_anomaly_cases.id", ondelete="CASCADE"), nullable=False),
        sa.Column("action", sa.String(50), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("note", sa.Text()),
        sa.Column("actor_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("metadata_json", postgresql.JSONB()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_revenue_anomaly_events_case", "revenue_anomaly_events", ["case_id","created_at"])

def downgrade():
    op.drop_index("ix_revenue_anomaly_events_case", table_name="revenue_anomaly_events")
    op.drop_table("revenue_anomaly_events")
    op.drop_index("ix_revenue_anomaly_cases_fingerprint", table_name="revenue_anomaly_cases")
    op.drop_index("ix_revenue_anomaly_cases_risk", table_name="revenue_anomaly_cases")
    op.drop_index("ix_revenue_anomaly_cases_facility_status", table_name="revenue_anomaly_cases")
    op.drop_table("revenue_anomaly_cases")
