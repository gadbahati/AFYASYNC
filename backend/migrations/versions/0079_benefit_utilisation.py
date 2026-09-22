"""benefit utilisation and rule extensions

Revision ID: 0079_benefit_utilisation
Revises: 0078_identity_membership
Create Date: 2026-09-22
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0079_benefit_utilisation"
down_revision = "0078_identity_membership"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "benefit_utilisation",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("coverage_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("coverage.id", ondelete="CASCADE"), nullable=False),
        sa.Column("person_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("persons.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("facility_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("facilities.id", ondelete="SET NULL")),
        sa.Column("service_code", sa.String(80), nullable=False),
        sa.Column("amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("calendar_year", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="POSTED"),
        sa.Column("reference", sa.String(120)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_benefit_utilisation_coverage_id", "benefit_utilisation", ["coverage_id"])
    op.create_index("ix_benefit_utilisation_person_id", "benefit_utilisation", ["person_id"])
    op.create_index("ix_benefit_utilisation_service_code", "benefit_utilisation", ["service_code"])
    op.create_index("ix_benefit_utilisation_calendar_year", "benefit_utilisation", ["calendar_year"])

    # Extend payer_benefit_rules for exclusion, preauth, annual limit, documents
    op.add_column("payer_benefit_rules", sa.Column("is_excluded", sa.Boolean(), server_default=sa.false(), nullable=False))
    op.add_column("payer_benefit_rules", sa.Column("requires_preauth", sa.Boolean(), server_default=sa.false(), nullable=False))
    op.add_column("payer_benefit_rules", sa.Column("annual_limit_amount", sa.Numeric(14, 2), nullable=True))
    op.add_column("payer_benefit_rules", sa.Column("required_documents", postgresql.JSONB(), nullable=True))


def downgrade() -> None:
    op.drop_column("payer_benefit_rules", "required_documents")
    op.drop_column("payer_benefit_rules", "annual_limit_amount")
    op.drop_column("payer_benefit_rules", "requires_preauth")
    op.drop_column("payer_benefit_rules", "is_excluded")
    op.drop_table("benefit_utilisation")
