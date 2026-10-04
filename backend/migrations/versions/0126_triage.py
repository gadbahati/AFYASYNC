"""Phase 128 — triage and acuity workflow."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0126_triage"
down_revision = "0125_identity_portal_separation"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "triage_assessments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("encounter_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("assessed_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("vital_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("acuity", sa.Integer(), nullable=False),
        sa.Column("priority", sa.String(20), nullable=False),
        sa.Column("chief_complaint", sa.Text(), nullable=True),
        sa.Column("red_flags", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("disposition", sa.String(40), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("assessed_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["encounter_id"], ["encounters.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["assessed_by"], ["staff.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["vital_id"], ["vitals.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_triage_assessments_encounter", "triage_assessments", ["encounter_id", "assessed_at"])
    op.create_index("ix_triage_assessments_priority", "triage_assessments", ["priority", "assessed_at"])


def downgrade():
    op.drop_index("ix_triage_assessments_priority", table_name="triage_assessments")
    op.drop_index("ix_triage_assessments_encounter", table_name="triage_assessments")
    op.drop_table("triage_assessments")
