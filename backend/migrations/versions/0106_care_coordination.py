"""care coordination cases
Revision ID: 0106_care_coordination
Revises: 0105_health_exchange
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
revision="0106_care_coordination";down_revision="0105_health_exchange";branch_labels=None;depends_on=None
def upgrade():
 op.create_table("care_coordination_cases",
  sa.Column("id",postgresql.UUID(as_uuid=True),primary_key=True),
  sa.Column("case_number",sa.String(80),nullable=False),
  sa.Column("referral_id",postgresql.UUID(as_uuid=True),sa.ForeignKey("referrals.id",ondelete="RESTRICT"),nullable=False),
  sa.Column("patient_id",postgresql.UUID(as_uuid=True),sa.ForeignKey("persons.id",ondelete="RESTRICT"),nullable=False),
  sa.Column("source_facility_id",postgresql.UUID(as_uuid=True),sa.ForeignKey("facilities.id",ondelete="RESTRICT"),nullable=False),
  sa.Column("destination_facility_id",postgresql.UUID(as_uuid=True),sa.ForeignKey("facilities.id",ondelete="RESTRICT"),nullable=False),
  sa.Column("status",sa.String(30),nullable=False,server_default="OPEN"),
  sa.Column("due_at",sa.DateTime(timezone=True)),sa.Column("accepted_at",sa.DateTime(timezone=True)),sa.Column("appointment_at",sa.DateTime(timezone=True)),sa.Column("handoff_at",sa.DateTime(timezone=True)),sa.Column("closed_at",sa.DateTime(timezone=True)),
  sa.Column("outcome",sa.Text()),sa.Column("notes",sa.Text()),sa.Column("evidence",postgresql.JSONB()),
  sa.Column("created_by",postgresql.UUID(as_uuid=True),sa.ForeignKey("users.id",ondelete="SET NULL")),
  sa.Column("created_at",sa.DateTime(timezone=True),server_default=sa.func.now()),sa.Column("updated_at",sa.DateTime(timezone=True),server_default=sa.func.now()),
  sa.UniqueConstraint("case_number",name="uq_care_coordination_case_number"))
 for n,cols in [("ix_care_coordination_status_due",["status","due_at"]),("ix_care_coordination_referral",["referral_id"]),("ix_care_coordination_patient",["patient_id"]),("ix_care_coordination_source_facility_id",["source_facility_id"]),("ix_care_coordination_destination_facility_id",["destination_facility_id"])]:
  op.create_index(n,"care_coordination_cases",cols)
def downgrade():
 for n in ["ix_care_coordination_destination_facility_id","ix_care_coordination_source_facility_id","ix_care_coordination_patient","ix_care_coordination_referral","ix_care_coordination_status_due"]:op.drop_index(n,table_name="care_coordination_cases")
 op.drop_table("care_coordination_cases")
