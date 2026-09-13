"""add emergency and triage workflow

Revision ID: 0036_emergency
Revises: 0035_lab_catalogue_permission
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0036_emergency"
down_revision = "0035_lab_catalogue_permission"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "emergency_visits",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("visit_number", sa.String(40), nullable=False, unique=True),
        sa.Column("patient_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("persons.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("facility_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("facilities.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("encounter_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("encounters.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("arrival_mode", sa.String(40), nullable=True),
        sa.Column("chief_complaint", sa.Text(), nullable=True),
        sa.Column("triage_level", sa.String(20), nullable=False, server_default="URGENT"),
        sa.Column("status", sa.String(30), nullable=False, server_default="WAITING"),
        sa.Column("disposition", sa.String(40), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("arrived_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_emergency_visits_patient_id", "emergency_visits", ["patient_id"])
    op.create_index("ix_emergency_visits_facility_id", "emergency_visits", ["facility_id"])
    op.create_index("ix_emergency_visits_encounter_id", "emergency_visits", ["encounter_id"])
    op.create_index("ix_emergency_visits_triage_level", "emergency_visits", ["triage_level"])
    op.create_index("ix_emergency_visits_status", "emergency_visits", ["status"])
    op.create_index("ix_emergency_visits_arrived_at", "emergency_visits", ["arrived_at"])

    op.create_table(
        "emergency_triage",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("visit_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("emergency_visits.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("recorded_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("staff.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("temperature", sa.String(20), nullable=True),
        sa.Column("heart_rate", sa.String(20), nullable=True),
        sa.Column("respiratory_rate", sa.String(20), nullable=True),
        sa.Column("systolic_bp", sa.String(20), nullable=True),
        sa.Column("diastolic_bp", sa.String(20), nullable=True),
        sa.Column("oxygen_saturation", sa.String(20), nullable=True),
        sa.Column("pain_score", sa.Integer(), nullable=True),
        sa.Column("consciousness", sa.String(40), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("recorded_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_emergency_triage_visit_id", "emergency_triage", ["visit_id"])
    op.create_index("ix_emergency_triage_recorded_by", "emergency_triage", ["recorded_by"])


def downgrade() -> None:
    op.drop_table("emergency_triage")
    op.drop_table("emergency_visits")
