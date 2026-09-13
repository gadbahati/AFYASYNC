"""dietetics assessment and diet orders
Revision ID: 0044_dietetics
Revises: 0043_patient_safety
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
revision="0044_dietetics";down_revision="0043_patient_safety";branch_labels=None;depends_on=None

def upgrade():
 op.create_table("nutrition_assessments",sa.Column("id",postgresql.UUID(as_uuid=True),primary_key=True),sa.Column("facility_id",postgresql.UUID(as_uuid=True),sa.ForeignKey("facilities.id",ondelete="RESTRICT"),nullable=False),sa.Column("patient_id",postgresql.UUID(as_uuid=True),sa.ForeignKey("persons.id",ondelete="RESTRICT"),nullable=False),sa.Column("encounter_id",postgresql.UUID(as_uuid=True),sa.ForeignKey("encounters.id",ondelete="RESTRICT")),sa.Column("weight",sa.String(30)),sa.Column("height",sa.String(30)),sa.Column("bmi",sa.Numeric(8,2)),sa.Column("nutrition_risk",sa.String(40),nullable=False,server_default="LOW"),sa.Column("dietary_requirements",sa.Text),sa.Column("allergies",sa.Text),sa.Column("notes",sa.Text),sa.Column("assessed_by",postgresql.UUID(as_uuid=True),sa.ForeignKey("staff.id",ondelete="RESTRICT"),nullable=False),sa.Column("assessed_at",sa.DateTime(timezone=True),server_default=sa.func.now(),nullable=False))
 op.create_table("diet_orders",sa.Column("id",postgresql.UUID(as_uuid=True),primary_key=True),sa.Column("facility_id",postgresql.UUID(as_uuid=True),sa.ForeignKey("facilities.id",ondelete="RESTRICT"),nullable=False),sa.Column("patient_id",postgresql.UUID(as_uuid=True),sa.ForeignKey("persons.id",ondelete="RESTRICT"),nullable=False),sa.Column("encounter_id",postgresql.UUID(as_uuid=True),sa.ForeignKey("encounters.id",ondelete="RESTRICT")),sa.Column("diet_type",sa.String(80),nullable=False),sa.Column("texture",sa.String(60)),sa.Column("calories",sa.String(40)),sa.Column("restrictions",sa.Text),sa.Column("instructions",sa.Text),sa.Column("status",sa.String(30),nullable=False,server_default="ACTIVE"),sa.Column("ordered_by",postgresql.UUID(as_uuid=True),sa.ForeignKey("staff.id",ondelete="RESTRICT"),nullable=False),sa.Column("ordered_at",sa.DateTime(timezone=True),server_default=sa.func.now(),nullable=False))

def downgrade():
 op.drop_table("diet_orders");op.drop_table("nutrition_assessments")
