"""universal claims clearinghouse
Revision ID: 0110_claim_clearinghouse
Revises: 0109_provider_contracting
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0110_claim_clearinghouse"
down_revision = "0109_provider_contracting"
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        "clearinghouse_routes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("facility_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("facilities.id", ondelete="CASCADE"), nullable=False),
        sa.Column("payer_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("payers.id", ondelete="CASCADE")),
        sa.Column("source_type", sa.String(40), nullable=False),
        sa.Column("adapter_code", sa.String(80), nullable=False),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="100"),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("supports_submission", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("supports_callback", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("configuration", postgresql.JSONB()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("facility_id", "payer_id", "source_type", "adapter_code", name="uq_clearinghouse_route"),
    )
    op.create_index("ix_clearinghouse_routes_facility", "clearinghouse_routes", ["facility_id", "active"])
    op.create_index("ix_clearinghouse_routes_payer", "clearinghouse_routes", ["payer_id", "source_type"])

    op.create_table(
        "clearinghouse_cases",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("case_number", sa.String(90), unique=True, nullable=False),
        sa.Column("facility_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("facilities.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("claim_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("claims.id", ondelete="SET NULL")),
        sa.Column("invoice_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("invoices.id", ondelete="SET NULL")),
        sa.Column("patient_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("persons.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("payer_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("payers.id", ondelete="SET NULL")),
        sa.Column("source_type", sa.String(40), nullable=False),
        sa.Column("adapter_code", sa.String(80)),
        sa.Column("status", sa.String(40), nullable=False, server_default="INTAKE"),
        sa.Column("idempotency_key", sa.String(180), nullable=False),
        sa.Column("claim_amount", sa.Numeric(14,2), nullable=False, server_default="0"),
        sa.Column("approved_amount", sa.Numeric(14,2), nullable=False, server_default="0"),
        sa.Column("paid_amount", sa.Numeric(14,2), nullable=False, server_default="0"),
        sa.Column("external_reference", sa.String(180)),
        sa.Column("denial_code", sa.String(80)),
        sa.Column("denial_category", sa.String(60)),
        sa.Column("denial_message", sa.Text()),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_error", sa.Text()),
        sa.Column("queued_at", sa.DateTime(timezone=True)),
        sa.Column("submitted_at", sa.DateTime(timezone=True)),
        sa.Column("acknowledged_at", sa.DateTime(timezone=True)),
        sa.Column("resolved_at", sa.DateTime(timezone=True)),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("facility_id", "idempotency_key", name="uq_clearinghouse_case_idempotency"),
    )
    op.create_index("ix_clearinghouse_cases_facility_status", "clearinghouse_cases", ["facility_id", "status"])
    op.create_index("ix_clearinghouse_cases_payer_status", "clearinghouse_cases", ["payer_id", "status"])
    op.create_index("ix_clearinghouse_cases_external", "clearinghouse_cases", ["external_reference"])
    op.create_index("ix_clearinghouse_cases_claim", "clearinghouse_cases", ["claim_id"])

    op.create_table(
        "clearinghouse_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("case_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("clearinghouse_cases.id", ondelete="CASCADE"), nullable=False),
        sa.Column("event_type", sa.String(60), nullable=False),
        sa.Column("from_status", sa.String(40)),
        sa.Column("to_status", sa.String(40)),
        sa.Column("actor_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("message", sa.Text()),
        sa.Column("metadata", postgresql.JSONB()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_clearinghouse_events_case", "clearinghouse_events", ["case_id", "created_at"])

    op.create_table(
        "clearinghouse_denial_codes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("code", sa.String(80), unique=True, nullable=False),
        sa.Column("category", sa.String(60), nullable=False),
        sa.Column("title", sa.String(180), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("recommended_action", sa.Text()),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.create_index("ix_clearinghouse_denial_codes_category", "clearinghouse_denial_codes", ["category", "active"])

    op.create_table(
        "clearinghouse_remittances",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("case_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("clearinghouse_cases.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("external_reference", sa.String(180)),
        sa.Column("status", sa.String(30), nullable=False, server_default="RECEIVED"),
        sa.Column("approved_amount", sa.Numeric(14,2), nullable=False, server_default="0"),
        sa.Column("paid_amount", sa.Numeric(14,2), nullable=False, server_default="0"),
        sa.Column("patient_amount", sa.Numeric(14,2), nullable=False, server_default="0"),
        sa.Column("currency", sa.String(3), nullable=False, server_default="KES"),
        sa.Column("received_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("metadata", postgresql.JSONB()),
    )
    op.create_index("ix_clearinghouse_remittances_case", "clearinghouse_remittances", ["case_id", "received_at"])

def downgrade():
    op.drop_index("ix_clearinghouse_remittances_case", table_name="clearinghouse_remittances")
    op.drop_table("clearinghouse_remittances")
    op.drop_index("ix_clearinghouse_denial_codes_category", table_name="clearinghouse_denial_codes")
    op.drop_table("clearinghouse_denial_codes")
    op.drop_index("ix_clearinghouse_events_case", table_name="clearinghouse_events")
    op.drop_table("clearinghouse_events")
    op.drop_index("ix_clearinghouse_cases_claim", table_name="clearinghouse_cases")
    op.drop_index("ix_clearinghouse_cases_external", table_name="clearinghouse_cases")
    op.drop_index("ix_clearinghouse_cases_payer_status", table_name="clearinghouse_cases")
    op.drop_index("ix_clearinghouse_cases_facility_status", table_name="clearinghouse_cases")
    op.drop_table("clearinghouse_cases")
    op.drop_index("ix_clearinghouse_routes_payer", table_name="clearinghouse_routes")
    op.drop_index("ix_clearinghouse_routes_facility", table_name="clearinghouse_routes")
    op.drop_table("clearinghouse_routes")
