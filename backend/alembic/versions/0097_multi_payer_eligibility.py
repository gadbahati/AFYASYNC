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
    op.create_index("ix_eligibility_decisions_person_id", "eligibility_decisions", ["person_id"])
    op.create_index("ix_eligibility_decisions_payer_id", "eligibility_decisions", ["payer_id"])
    op.create_index("ix_eligibility_decisions_payer_plan_id", "eligibility_decisions", ["payer_plan_id"])
    op.create_index("ix_eligibility_decisions_service_code", "eligibility_decisions", ["service_code"])
    op.create_index("ix_eligibility_decisions_service_type", "eligibility_decisions", ["service_type"])
    op.create_index("ix_eligibility_decisions_coverage_id", "eligibility_decisions", ["coverage_id"])

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
    op.create_index("ix_financing_person_identifiers_person_id", "financing_person_identifiers", ["person_id"])
    op.create_index("ix_financing_person_identifiers_identifier_hash", "financing_person_identifiers", ["identifier_hash"])
    op.create_index("ix_financing_person_identifiers_payer_id", "financing_person_identifiers", ["payer_id"])


def downgrade() -> None:
    op.drop_index("ix_financing_person_identifiers_payer_id", table_name="financing_person_identifiers")
    op.drop_index("ix_financing_person_identifiers_identifier_hash", table_name="financing_person_identifiers")
    op.drop_index("ix_financing_person_identifiers_person_id", table_name="financing_person_identifiers")
    op.drop_table("financing_person_identifiers")
    op.drop_index("ix_eligibility_decisions_coverage_id", table_name="eligibility_decisions")
    op.drop_index("ix_eligibility_decisions_service_type", table_name="eligibility_decisions")
    op.drop_index("ix_eligibility_decisions_service_code", table_name="eligibility_decisions")
    op.drop_index("ix_eligibility_decisions_payer_plan_id", table_name="eligibility_decisions")
    op.drop_index("ix_eligibility_decisions_payer_id", table_name="eligibility_decisions")
    op.drop_index("ix_eligibility_decisions_person_id", table_name="eligibility_decisions")
    op.drop_table("eligibility_decisions")
