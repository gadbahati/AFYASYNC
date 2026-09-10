"""add clinical encounter records

Revision ID: 0006_clinical
Revises: 0005_appointments_encounters_queue
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0006_clinical"
down_revision = "0005_appointments_encounters_queue"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "consultations",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("encounter_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("doctor_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("chief_complaint", sa.Text(), nullable=True),
        sa.Column("history", sa.Text(), nullable=True),
        sa.Column("examination", sa.Text(), nullable=True),
        sa.Column("assessment", sa.Text(), nullable=True),
        sa.Column("clinical_notes", sa.Text(), nullable=True),
        sa.Column("treatment_plan", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["encounter_id"], ["encounters.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["doctor_id"], ["staff.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("encounter_id"),
    )
    op.create_index("ix_consultations_encounter_id", "consultations", ["encounter_id"])

    op.create_table(
        "vitals",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("encounter_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("recorded_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("systolic_bp", sa.Integer(), nullable=True),
        sa.Column("diastolic_bp", sa.Integer(), nullable=True),
        sa.Column("pulse", sa.Integer(), nullable=True),
        sa.Column("temperature_c", sa.Numeric(4, 1), nullable=True),
        sa.Column("respiratory_rate", sa.Integer(), nullable=True),
        sa.Column("oxygen_saturation", sa.Numeric(5, 2), nullable=True),
        sa.Column("weight_kg", sa.Numeric(6, 2), nullable=True),
        sa.Column("height_cm", sa.Numeric(6, 2), nullable=True),
        sa.Column("bmi", sa.Numeric(5, 2), nullable=True),
        sa.Column("recorded_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["encounter_id"], ["encounters.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["recorded_by"], ["staff.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_vitals_encounter_id", "vitals", ["encounter_id"])

    op.create_table(
        "diagnoses",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("encounter_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("diagnosis_code", sa.String(length=50), nullable=True),
        sa.Column("diagnosis_name", sa.String(length=250), nullable=False),
        sa.Column("diagnosis_type", sa.String(length=30), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("recorded_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["encounter_id"], ["encounters.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["recorded_by"], ["staff.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_diagnoses_encounter_id", "diagnoses", ["encounter_id"])


def downgrade() -> None:
    op.drop_index("ix_diagnoses_encounter_id", table_name="diagnoses")
    op.drop_table("diagnoses")
    op.drop_index("ix_vitals_encounter_id", table_name="vitals")
    op.drop_table("vitals")
    op.drop_index("ix_consultations_encounter_id", table_name="consultations")
    op.drop_table("consultations")
