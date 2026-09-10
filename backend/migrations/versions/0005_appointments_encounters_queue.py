"""add appointments encounters and queues

Revision ID: 0005_appointments_encounters_queue
Revises: 0004_rbac
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0005_appointments_encounters_queue"
down_revision = "0004_rbac"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_sequence("afasync_encounter_seq", start=1)

    op.create_table(
        "encounters",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("encounter_id", sa.String(length=40), nullable=False),
        sa.Column("patient_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("facility_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("department_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("encounter_type", sa.String(length=30), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["patient_id"], ["persons.id"]),
        sa.ForeignKeyConstraint(["facility_id"], ["facilities.id"]),
        sa.ForeignKeyConstraint(["department_id"], ["departments.id"]),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("encounter_id"),
    )
    for name, column in [("patient_id", "patient_id"), ("facility_id", "facility_id"), ("department_id", "department_id"), ("status", "status"), ("encounter_id", "encounter_id")]:
        op.create_index(f"ix_encounters_{name}", "encounters", [column])

    op.create_table(
        "appointments",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("patient_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("facility_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("department_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("provider_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("appointment_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["patient_id"], ["persons.id"]),
        sa.ForeignKeyConstraint(["facility_id"], ["facilities.id"]),
        sa.ForeignKeyConstraint(["department_id"], ["departments.id"]),
        sa.ForeignKeyConstraint(["provider_id"], ["staff.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    for name in ("patient_id", "facility_id", "department_id", "provider_id", "appointment_at", "status"):
        op.create_index(f"ix_appointments_{name}", "appointments", [name])

    op.create_table(
        "queues",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("facility_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("department_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["facility_id"], ["facilities.id"]),
        sa.ForeignKeyConstraint(["department_id"], ["departments.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_queues_facility_id", "queues", ["facility_id"])
    op.create_index("ix_queues_department_id", "queues", ["department_id"])
    op.create_index("ix_queues_status", "queues", ["status"])

    op.create_table(
        "queue_entries",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("queue_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("patient_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("appointment_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("encounter_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("priority", sa.String(length=20), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("queued_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("called_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["queue_id"], ["queues.id"]),
        sa.ForeignKeyConstraint(["patient_id"], ["persons.id"]),
        sa.ForeignKeyConstraint(["appointment_id"], ["appointments.id"]),
        sa.ForeignKeyConstraint(["encounter_id"], ["encounters.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    for name in ("queue_id", "patient_id", "appointment_id", "encounter_id", "status", "queued_at"):
        op.create_index(f"ix_queue_entries_{name}", "queue_entries", [name])


def downgrade() -> None:
    for name in ("queued_at", "status", "encounter_id", "appointment_id", "patient_id", "queue_id"):
        op.drop_index(f"ix_queue_entries_{name}", table_name="queue_entries")
    op.drop_table("queue_entries")
    op.drop_index("ix_queues_status", table_name="queues")
    op.drop_index("ix_queues_department_id", table_name="queues")
    op.drop_index("ix_queues_facility_id", table_name="queues")
    op.drop_table("queues")
    for name in ("status", "appointment_at", "provider_id", "department_id", "facility_id", "patient_id"):
        op.drop_index(f"ix_appointments_{name}", table_name="appointments")
    op.drop_table("appointments")
    for name in ("encounter_id", "status", "department_id", "facility_id", "patient_id"):
        op.drop_index(f"ix_encounters_{name}", table_name="encounters")
    op.drop_table("encounters")
    op.drop_sequence("afasync_encounter_seq")
