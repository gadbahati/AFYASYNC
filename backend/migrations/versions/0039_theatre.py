"""add theatre surgical workflow
Revision ID: 0039_theatre
Revises: 0038_wards_beds
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
revision="0039_theatre"; down_revision="0038_wards_beds"; branch_labels=None; depends_on=None

def upgrade():
    op.create_table("theatre_procedures",sa.Column("id",postgresql.UUID(as_uuid=True),primary_key=True),sa.Column("facility_id",postgresql.UUID(as_uuid=True),sa.ForeignKey("facilities.id",ondelete="RESTRICT"),nullable=False),sa.Column("code",sa.String(40),nullable=False),sa.Column("name",sa.String(160),nullable=False),sa.Column("description",sa.Text()),sa.Column("status",sa.String(20),nullable=False,server_default="ACTIVE"))
    op.create_index("ix_theatre_procedures_facility_id","theatre_procedures",["facility_id"])
    op.create_table("theatre_bookings",sa.Column("id",postgresql.UUID(as_uuid=True),primary_key=True),sa.Column("patient_id",postgresql.UUID(as_uuid=True),sa.ForeignKey("persons.id",ondelete="RESTRICT"),nullable=False),sa.Column("facility_id",postgresql.UUID(as_uuid=True),sa.ForeignKey("facilities.id",ondelete="RESTRICT"),nullable=False),sa.Column("encounter_id",postgresql.UUID(as_uuid=True),sa.ForeignKey("encounters.id",ondelete="RESTRICT")),sa.Column("procedure_id",postgresql.UUID(as_uuid=True),sa.ForeignKey("theatre_procedures.id",ondelete="RESTRICT"),nullable=False),sa.Column("surgeon_id",postgresql.UUID(as_uuid=True),sa.ForeignKey("staff.id",ondelete="RESTRICT")),sa.Column("anaesthetist_id",postgresql.UUID(as_uuid=True),sa.ForeignKey("staff.id",ondelete="RESTRICT")),sa.Column("scheduled_at",sa.DateTime(timezone=True),nullable=False),sa.Column("status",sa.String(30),nullable=False,server_default="SCHEDULED"),sa.Column("indication",sa.Text()),sa.Column("created_at",sa.DateTime(timezone=True),server_default=sa.func.now(),nullable=False))
    op.create_index("ix_theatre_bookings_patient_id","theatre_bookings",["patient_id"]); op.create_index("ix_theatre_bookings_facility_id","theatre_bookings",["facility_id"]); op.create_index("ix_theatre_bookings_scheduled_at","theatre_bookings",["scheduled_at"])
    op.create_table("theatre_records",sa.Column("id",postgresql.UUID(as_uuid=True),primary_key=True),sa.Column("booking_id",postgresql.UUID(as_uuid=True),sa.ForeignKey("theatre_bookings.id",ondelete="RESTRICT"),nullable=False,unique=True),sa.Column("anaesthesia_type",sa.String(50)),sa.Column("preoperative_notes",sa.Text()),sa.Column("procedure_notes",sa.Text(),nullable=False),sa.Column("postoperative_notes",sa.Text()),sa.Column("complications",sa.Text()),sa.Column("outcome",sa.String(80)),sa.Column("recorded_by",postgresql.UUID(as_uuid=True),sa.ForeignKey("staff.id",ondelete="RESTRICT"),nullable=False),sa.Column("completed_at",sa.DateTime(timezone=True),server_default=sa.func.now(),nullable=False))

def downgrade(): op.drop_table("theatre_records"); op.drop_table("theatre_bookings"); op.drop_table("theatre_procedures")
