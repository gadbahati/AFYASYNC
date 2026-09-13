"""infection prevention and control records
Revision ID: 0045_infection_control
Revises: 0044_dietetics
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0045_infection_control"
down_revision = "0044_dietetics"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "infection_incidents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("facility_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("facilities.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("patient_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("persons.id", ondelete="RESTRICT")),
        sa.Column("encounter_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("encounters.id", ondelete="RESTRICT")),
        sa.Column("incident_type", sa.String(80), nullable=False),
        sa.Column("suspected_infection", sa.String(160)),
        sa.Column("specimen_collected", sa.String(120)),
        sa.Column("onset_at", sa.DateTime(timezone=True)),
        sa.Column("severity", sa.String(30), nullable=False, server_default="MODERATE"),
        sa.Column("status", sa.String(30), nullable=False, server_default="OPEN"),
        sa.Column("isolation_required", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("notes", sa.Text),
        sa.Column("reported_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("staff.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_infection_incidents_facility_id", "infection_incidents", ["facility_id"])
    op.create_index("ix_infection_incidents_patient_id", "infection_incidents", ["patient_id"])
    op.create_index("ix_infection_incidents_encounter_id", "infection_incidents", ["encounter_id"])

    op.create_table(
        "isolation_precautions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("facility_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("facilities.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("patient_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("persons.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("encounter_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("encounters.id", ondelete="RESTRICT")),
        sa.Column("precaution_type", sa.String(60), nullable=False),
        sa.Column("reason", sa.Text),
        sa.Column("status", sa.String(30), nullable=False, server_default="ACTIVE"),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("ended_at", sa.DateTime(timezone=True)),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("staff.id", ondelete="RESTRICT"), nullable=False),
    )
    op.create_index("ix_isolation_precautions_facility_id", "isolation_precautions", ["facility_id"])
    op.create_index("ix_isolation_precautions_patient_id", "isolation_precautions", ["patient_id"])


def downgrade():
    op.drop_table("isolation_precautions")
    op.drop_table("infection_incidents")
