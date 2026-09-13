"""patient safety incident reporting and permissions
Revision ID: 0043_patient_safety
Revises: 0042_blood_bank
"""
from uuid import uuid4
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
revision="0043_patient_safety";down_revision="0042_blood_bank";branch_labels=None;depends_on=None
PERMISSIONS=(("patient_safety.write","Report patient safety incidents"),("patient_safety.manage","Review and manage patient safety incidents"))
ROLES=("Doctor","Nurse","Hospital Administrator","System Administrator")
def upgrade():
 op.create_table("safety_incidents",sa.Column("id",postgresql.UUID(as_uuid=True),primary_key=True),sa.Column("facility_id",postgresql.UUID(as_uuid=True),sa.ForeignKey("facilities.id",ondelete="RESTRICT"),nullable=False),sa.Column("patient_id",postgresql.UUID(as_uuid=True),sa.ForeignKey("persons.id",ondelete="RESTRICT")),sa.Column("encounter_id",postgresql.UUID(as_uuid=True),sa.ForeignKey("encounters.id",ondelete="RESTRICT")),sa.Column("incident_number",sa.String(60),unique=True,nullable=False),sa.Column("category",sa.String(60),nullable=False),sa.Column("severity",sa.String(30),nullable=False,server_default="LOW"),sa.Column("event_type",sa.String(30),nullable=False,server_default="INCIDENT"),sa.Column("occurred_at",sa.DateTime(timezone=True),nullable=False),sa.Column("location",sa.String(120)),sa.Column("description",sa.Text,nullable=False),sa.Column("immediate_action",sa.Text),sa.Column("status",sa.String(30),nullable=False,server_default="OPEN"),sa.Column("reported_by",postgresql.UUID(as_uuid=True),sa.ForeignKey("staff.id",ondelete="RESTRICT"),nullable=False),sa.Column("corrective_action",sa.Text),sa.Column("root_cause",sa.Text),sa.Column("closed_at",sa.DateTime(timezone=True)),sa.Column("closed_by",postgresql.UUID(as_uuid=True),sa.ForeignKey("staff.id",ondelete="RESTRICT")),sa.Column("created_at",sa.DateTime(timezone=True),server_default=sa.func.now(),nullable=False))
 op.create_index("ix_safety_incidents_facility_id","safety_incidents",["facility_id"]);op.create_index("ix_safety_incidents_patient_id","safety_incidents",["patient_id"]);op.create_index("ix_safety_incidents_status","safety_incidents",["status"])
 bind=op.get_bind();permissions=sa.table("permissions",sa.column("id"),sa.column("code"),sa.column("description"));roles=sa.table("roles",sa.column("id"),sa.column("name"));rp=sa.table("role_permissions",sa.column("role_id"),sa.column("permission_id"))
 for code,desc in PERMISSIONS:
  pid=bind.execute(sa.select(permissions.c.id).where(permissions.c.code==code)).scalar()
  if pid is None: bind.execute(sa.insert(permissions).values(id=uuid4(),code=code,description=desc))
 for rid,rname in bind.execute(sa.select(roles.c.id,roles.c.name).where(roles.c.name.in_(ROLES))).fetchall():
  for code,_ in PERMISSIONS:
   pid=bind.execute(sa.select(permissions.c.id).where(permissions.c.code==code)).scalar_one()
   if bind.execute(sa.select(rp.c.role_id).where(rp.c.role_id==rid,rp.c.permission_id==pid)).first() is None: bind.execute(sa.insert(rp).values(role_id=rid,permission_id=pid))
def downgrade():
 bind=op.get_bind();permissions=sa.table("permissions",sa.column("id"),sa.column("code"));rp=sa.table("role_permissions",sa.column("permission_id"));ids=[r[0] for r in bind.execute(sa.select(permissions.c.id).where(permissions.c.code.in_([p[0] for p in PERMISSIONS]))).fetchall()]
 if ids: bind.execute(sa.delete(rp).where(rp.c.permission_id.in_(ids)));bind.execute(sa.delete(permissions).where(permissions.c.id.in_(ids)))
 op.drop_table("safety_incidents")
