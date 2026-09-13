"""child health growth and immunisation
Revision ID: 0041_child_health
Revises: 0040_maternity
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
revision="0041_child_health";down_revision="0040_maternity";branch_labels=None;depends_on=None

def upgrade():
 op.create_table("child_health_records",sa.Column("id",postgresql.UUID(as_uuid=True),primary_key=True),sa.Column("patient_id",postgresql.UUID(as_uuid=True),sa.ForeignKey("persons.id",ondelete="RESTRICT"),nullable=False),sa.Column("facility_id",postgresql.UUID(as_uuid=True),sa.ForeignKey("facilities.id",ondelete="RESTRICT"),nullable=False),sa.Column("mother_id",postgresql.UUID(as_uuid=True),sa.ForeignKey("persons.id",ondelete="RESTRICT")),sa.Column("birth_date",sa.Date),sa.Column("birth_weight",sa.String(30)),sa.Column("notes",sa.Text),sa.Column("status",sa.String(20),nullable=False,server_default="ACTIVE"))
 op.create_table("growth_observations",sa.Column("id",postgresql.UUID(as_uuid=True),primary_key=True),sa.Column("child_id",postgresql.UUID(as_uuid=True),sa.ForeignKey("child_health_records.id",ondelete="RESTRICT"),nullable=False),sa.Column("facility_id",postgresql.UUID(as_uuid=True),sa.ForeignKey("facilities.id",ondelete="RESTRICT"),nullable=False),sa.Column("observed_at",sa.DateTime(timezone=True),server_default=sa.func.now(),nullable=False),sa.Column("age_months",sa.Integer),sa.Column("weight",sa.String(30)),sa.Column("height",sa.String(30)),sa.Column("head_circumference",sa.String(30)),sa.Column("assessment",sa.Text),sa.Column("recorded_by",postgresql.UUID(as_uuid=True),sa.ForeignKey("staff.id",ondelete="RESTRICT"),nullable=False))
 op.create_table("immunisations",sa.Column("id",postgresql.UUID(as_uuid=True),primary_key=True),sa.Column("child_id",postgresql.UUID(as_uuid=True),sa.ForeignKey("child_health_records.id",ondelete="RESTRICT"),nullable=False),sa.Column("facility_id",postgresql.UUID(as_uuid=True),sa.ForeignKey("facilities.id",ondelete="RESTRICT"),nullable=False),sa.Column("vaccine",sa.String(120),nullable=False),sa.Column("dose",sa.String(40),nullable=False),sa.Column("administered_at",sa.DateTime(timezone=True),server_default=sa.func.now(),nullable=False),sa.Column("next_due_at",sa.DateTime(timezone=True)),sa.Column("batch_number",sa.String(80)),sa.Column("recorded_by",postgresql.UUID(as_uuid=True),sa.ForeignKey("staff.id",ondelete="RESTRICT"),nullable=False),sa.Column("notes",sa.Text))

def downgrade():
 op.drop_table("immunisations");op.drop_table("growth_observations");op.drop_table("child_health_records")
