"""add wards beds and assignments
Revision ID: 0038_wards_beds
Revises: 0037_nursing
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
revision="0038_wards_beds"
down_revision="0037_nursing"
branch_labels=None
depends_on=None

def upgrade():
    op.create_table("wards", sa.Column("id",postgresql.UUID(as_uuid=True),primary_key=True), sa.Column("facility_id",postgresql.UUID(as_uuid=True),sa.ForeignKey("facilities.id",ondelete="RESTRICT"),nullable=False), sa.Column("name",sa.String(120),nullable=False), sa.Column("ward_type",sa.String(50),nullable=False,server_default="GENERAL"), sa.Column("status",sa.String(20),nullable=False,server_default="ACTIVE"), sa.Column("created_at",sa.DateTime(timezone=True),server_default=sa.func.now(),nullable=False), sa.UniqueConstraint("facility_id","name",name="uq_ward_facility_name"))
    op.create_index("ix_wards_facility_id","wards",["facility_id"])
    op.create_table("beds", sa.Column("id",postgresql.UUID(as_uuid=True),primary_key=True), sa.Column("ward_id",postgresql.UUID(as_uuid=True),sa.ForeignKey("wards.id",ondelete="RESTRICT"),nullable=False), sa.Column("bed_number",sa.String(50),nullable=False), sa.Column("status",sa.String(30),nullable=False,server_default="AVAILABLE"), sa.Column("created_at",sa.DateTime(timezone=True),server_default=sa.func.now(),nullable=False), sa.UniqueConstraint("ward_id","bed_number",name="uq_bed_ward_number"))
    op.create_index("ix_beds_ward_id","beds",["ward_id"]); op.create_index("ix_beds_status","beds",["status"])
    op.create_table("bed_assignments", sa.Column("id",postgresql.UUID(as_uuid=True),primary_key=True), sa.Column("bed_id",postgresql.UUID(as_uuid=True),sa.ForeignKey("beds.id",ondelete="RESTRICT"),nullable=False), sa.Column("admission_id",postgresql.UUID(as_uuid=True),sa.ForeignKey("admissions.id",ondelete="RESTRICT"),nullable=False), sa.Column("assigned_by",postgresql.UUID(as_uuid=True),sa.ForeignKey("staff.id",ondelete="RESTRICT"),nullable=False), sa.Column("assigned_at",sa.DateTime(timezone=True),server_default=sa.func.now(),nullable=False), sa.Column("released_at",sa.DateTime(timezone=True)))
    op.create_index("ix_bed_assignments_bed_id","bed_assignments",["bed_id"]); op.create_index("ix_bed_assignments_admission_id","bed_assignments",["admission_id"])

def downgrade():
    op.drop_table("bed_assignments"); op.drop_table("beds"); op.drop_table("wards")
