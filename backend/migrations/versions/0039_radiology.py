"""add radiology catalogue orders and reports
Revision ID: 0039_radiology
Revises: 0038_wards_beds
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
revision="0039_radiology"; down_revision="0038_wards_beds"; branch_labels=None; depends_on=None

def upgrade():
 op.create_table("imaging_tests",sa.Column("id",postgresql.UUID(as_uuid=True),primary_key=True),sa.Column("facility_id",postgresql.UUID(as_uuid=True),sa.ForeignKey("facilities.id",ondelete="RESTRICT"),nullable=False),sa.Column("code",sa.String(40),nullable=False),sa.Column("name",sa.String(160),nullable=False),sa.Column("modality",sa.String(50),nullable=False),sa.Column("description",sa.Text()),sa.Column("price",sa.Numeric(12,2),nullable=False,server_default="0"),sa.Column("active",sa.Boolean(),nullable=False,server_default=sa.true()))
 op.create_index("ix_imaging_tests_facility_id","imaging_tests",["facility_id"])
 op.create_table("imaging_orders",sa.Column("id",postgresql.UUID(as_uuid=True),primary_key=True),sa.Column("order_number",sa.String(50),unique=True,nullable=False),sa.Column("patient_id",postgresql.UUID(as_uuid=True),sa.ForeignKey("persons.id",ondelete="RESTRICT"),nullable=False),sa.Column("facility_id",postgresql.UUID(as_uuid=True),sa.ForeignKey("facilities.id",ondelete="RESTRICT"),nullable=False),sa.Column("encounter_id",postgresql.UUID(as_uuid=True),sa.ForeignKey("encounters.id",ondelete="RESTRICT")),sa.Column("test_id",postgresql.UUID(as_uuid=True),sa.ForeignKey("imaging_tests.id",ondelete="RESTRICT"),nullable=False),sa.Column("ordered_by",postgresql.UUID(as_uuid=True),sa.ForeignKey("staff.id",ondelete="RESTRICT"),nullable=False),sa.Column("clinical_indication",sa.Text()),sa.Column("status",sa.String(30),nullable=False,server_default="ORDERED"),sa.Column("ordered_at",sa.DateTime(timezone=True),server_default=sa.func.now(),nullable=False),sa.Column("completed_at",sa.DateTime(timezone=True)))
 op.create_index("ix_imaging_orders_patient_id","imaging_orders",["patient_id"]); op.create_index("ix_imaging_orders_facility_id","imaging_orders",["facility_id"]); op.create_index("ix_imaging_orders_status","imaging_orders",["status"])
 op.create_table("imaging_reports",sa.Column("id",postgresql.UUID(as_uuid=True),primary_key=True),sa.Column("order_id",postgresql.UUID(as_uuid=True),sa.ForeignKey("imaging_orders.id",ondelete="RESTRICT"),unique=True,nullable=False),sa.Column("performed_by",postgresql.UUID(as_uuid=True),sa.ForeignKey("staff.id",ondelete="RESTRICT")),sa.Column("findings",sa.Text(),nullable=False),sa.Column("impression",sa.Text()),sa.Column("reported_at",sa.DateTime(timezone=True),server_default=sa.func.now(),nullable=False))

def downgrade():
 op.drop_table("imaging_reports"); op.drop_table("imaging_orders"); op.drop_table("imaging_tests")
