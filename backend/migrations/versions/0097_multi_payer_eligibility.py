"""multi-payer eligibility engine

Revision ID: 0097_multi_payer_eligibility
Revises: 0096_residual_risks
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0097_multi_payer_eligibility"
down_revision = "0096_residual_risks"
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.create_table(
        "eligibility_decisions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("person_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("persons.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("payer_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("payers.id", ondelete="SET NULL"), nullable=True),
        sa.Column("payer_plan_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("payer_plans.id", ondelete="SET NULL"), nullable=True),
        sa.Column("service_code", sa.String(80), nullable=True),
        sa.Column("service_type", sa.String(60), nullable=True),
        sa.Column("decision", sa.String(30), nullable=False),
        sa.Column("reason_code", sa.String(60), nullable=False),
        sa.Column("coverage_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("coverage.id", ondelete="SET NULL"), nullable=True),
        sa.Column("estimated_payer_amount", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("estimated_patient_amount", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("evaluated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("evidence", postgresql.JSONB, nullable=True),
    )
    for name, col in [
        ("person_id","person_id"),("payer_id","payer_id"),("payer_plan_id","payer_plan_id"),
        ("service_code","service_code"),("service_type","service_type"),("coverage_id","coverage_id")
    ]:
        op.create_index("ix_eligibility_decisions_"+name, "eligibility_decisions", [col])
    op.create_table(
        "financing_person_identifiers",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("person_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("persons.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("identifier_type", sa.String(40), nullable=False),
        sa.Column("identifier_hash", sa.String(128), nullable=False),
        sa.Column("payer_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("payers.id", ondelete="SET NULL"), nullable=True),
        sa.Column("status", sa.String(30), nullable=False, server_default="ACTIVE"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    for name, col in [("person_id","person_id"),("identifier_hash","identifier_hash"),("payer_id","payer_id")]:
        op.create_index("ix_financing_person_identifiers_"+name, "financing_person_identifiers", [col])

def downgrade() -> None:
    for name in ["payer_id","identifier_hash","person_id"]:
        op.drop_index("ix_financing_person_identifiers_"+name, table_name="financing_person_identifiers")
    op.drop_table("financing_person_identifiers")
    for name in ["coverage_id","service_type","service_code","payer_plan_id","payer_id","person_id"]:
        op.drop_index("ix_eligibility_decisions_"+name, table_name="eligibility_decisions")
    op.drop_table("eligibility_decisions")
