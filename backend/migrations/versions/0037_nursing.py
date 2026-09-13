"""add nursing observations, notes and handovers

Revision ID: 0037_nursing
Revises: 0036_emergency
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0037_nursing"
down_revision = "0036_emergency"
branch_labels = None
depends_on = None


def upgrade():
    common = [
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("patient_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("persons.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("facility_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("facilities.id", ondelete="RESTRICT"), nullable=False),
    ]
    op.create_table("nursing_observations", *common,
        sa.Column("encounter_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("encounters.id", ondelete="RESTRICT")),
        sa.Column("recorded_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("staff.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("temperature", sa.String(20)), sa.Column("heart_rate", sa.String(20)), sa.Column("respiratory_rate", sa.String(20)),
        sa.Column("systolic_bp", sa.String(20)), sa.Column("diastolic_bp", sa.String(20)), sa.Column("oxygen_saturation", sa.String(20)),
        sa.Column("pain_score", sa.Integer()), sa.Column("notes", sa.Text()),
        sa.Column("recorded_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False))
    op.create_table("nursing_notes", *common,
        sa.Column("encounter_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("encounters.id", ondelete="RESTRICT")),
        sa.Column("author_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("staff.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("shift", sa.String(30)), sa.Column("note_type", sa.String(40), nullable=False, server_default="PROGRESS"),
        sa.Column("content", sa.Text(), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False))
    op.create_table("nursing_handovers",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("patient_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("persons.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("facility_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("facilities.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("from_shift", sa.String(30), nullable=False), sa.Column("to_shift", sa.String(30), nullable=False),
        sa.Column("handed_over_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("staff.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("received_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("staff.id", ondelete="RESTRICT")),
        sa.Column("summary", sa.Text(), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False))
    for table in ("nursing_observations", "nursing_notes", "nursing_handovers"):
        op.create_index(f"ix_{table}_patient_id", table, ["patient_id"])
        op.create_index(f"ix_{table}_facility_id", table, ["facility_id"])


def downgrade():
    op.drop_table("nursing_handovers")
    op.drop_table("nursing_notes")
    op.drop_table("nursing_observations")
