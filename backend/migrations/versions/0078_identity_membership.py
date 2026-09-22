"""identity household membership corrections

Revision ID: 0078_identity_membership
Revises: 0077_department_capacity
Create Date: 2026-09-22
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0078_identity_membership"
down_revision = "0077_department_capacity"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "households",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("head_person_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("persons.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("label", sa.String(200)),
        sa.Column("county", sa.String(100)),
        sa.Column("status", sa.String(30), nullable=False, server_default="ACTIVE"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_households_head_person_id", "households", ["head_person_id"])
    op.create_index("ix_households_status", "households", ["status"])

    op.create_table(
        "household_members",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("household_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("households.id", ondelete="CASCADE"), nullable=False),
        sa.Column("person_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("persons.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("relationship_to_head", sa.String(40), nullable=False),
        sa.Column("is_dependant", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("status", sa.String(30), nullable=False, server_default="ACTIVE"),
        sa.Column("effective_from", sa.Date()),
        sa.Column("effective_to", sa.Date()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("household_id", "person_id", name="uq_household_person"),
    )
    op.create_index("ix_household_members_household_id", "household_members", ["household_id"])
    op.create_index("ix_household_members_person", "household_members", ["person_id"])

    op.create_table(
        "membership_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("person_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("persons.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("payer_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("payers.id", ondelete="SET NULL"), nullable=True),
        sa.Column("membership_number", sa.String(100)),
        sa.Column("status", sa.String(30), nullable=False, server_default="ACTIVE"),
        sa.Column("scheme_code", sa.String(80)),
        sa.Column("effective_from", sa.Date()),
        sa.Column("effective_to", sa.Date()),
        sa.Column("employer_name", sa.String(200)),
        sa.Column("employer_pin", sa.String(50)),
        sa.Column("notes", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_membership_records_person_id", "membership_records", ["person_id"])
    op.create_index("ix_membership_person_status", "membership_records", ["person_id", "status"])
    op.create_index("ix_membership_records_membership_number", "membership_records", ["membership_number"])

    op.create_table(
        "contribution_entries",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("membership_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("membership_records.id", ondelete="CASCADE"), nullable=False),
        sa.Column("period_label", sa.String(40), nullable=False),
        sa.Column("amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False, server_default="KES"),
        sa.Column("paid_on", sa.Date()),
        sa.Column("source", sa.String(40), nullable=False, server_default="MANUAL"),
        sa.Column("status", sa.String(30), nullable=False, server_default="RECORDED"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_contribution_entries_membership_id", "contribution_entries", ["membership_id"])

    op.create_table(
        "identity_corrections",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("person_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("persons.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("field_name", sa.String(80), nullable=False),
        sa.Column("old_value_redacted", sa.String(500)),
        sa.Column("new_value_redacted", sa.String(500)),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="PENDING"),
        sa.Column("requested_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("reviewed_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("reviewed_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_identity_corrections_person_id", "identity_corrections", ["person_id"])

    op.create_table(
        "identity_match_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("facility_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("facilities.id", ondelete="SET NULL")),
        sa.Column("actor_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("outcome", sa.String(40), nullable=False),
        sa.Column("top_score", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("evidence_json", postgresql.JSONB()),
        sa.Column("candidate_person_ids", postgresql.JSONB()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_identity_match_logs_facility_id", "identity_match_logs", ["facility_id"])


def downgrade() -> None:
    op.drop_table("identity_match_logs")
    op.drop_table("identity_corrections")
    op.drop_table("contribution_entries")
    op.drop_table("membership_records")
    op.drop_table("household_members")
    op.drop_table("households")
