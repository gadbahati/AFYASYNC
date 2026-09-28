"""payer agnostic financing preauthorizations

Revision ID: 0099_financing_preauth
Revises: 0098_universal_identity
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision="0099_financing_preauth"
down_revision="0098_universal_identity"
branch_labels=None
depends_on=None

def upgrade():
    op.create_table(
        "financing_preauthorizations",
        sa.Column("id",postgresql.UUID(as_uuid=True),primary_key=True),
        sa.Column("authorization_number",sa.String(80),nullable=False,unique=True),
        sa.Column("person_id",postgresql.UUID(as_uuid=True),sa.ForeignKey("persons.id",ondelete="RESTRICT"),nullable=False),
        sa.Column("facility_id",postgresql.UUID(as_uuid=True),sa.ForeignKey("facilities.id",ondelete="RESTRICT"),nullable=False),
        sa.Column("coverage_id",postgresql.UUID(as_uuid=True),sa.ForeignKey("coverage.id",ondelete="RESTRICT"),nullable=False),
        sa.Column("payer_id",postgresql.UUID(as_uuid=True),sa.ForeignKey("payers.id",ondelete="RESTRICT"),nullable=False),
        sa.Column("service_code",sa.String(80)),
        sa.Column("service_type",sa.String(60)),
        sa.Column("requested_amount",sa.Numeric(14,2),nullable=False),
        sa.Column("approved_amount",sa.Numeric(14,2),nullable=False,server_default="0"),
        sa.Column("status",sa.String(40),nullable=False,server_default="PENDING"),
        sa.Column("decision_reason",sa.String(120)),
        sa.Column("external_reference",sa.String(150)),
        sa.Column("evidence",postgresql.JSONB),
        sa.Column("requested_at",sa.DateTime(timezone=True),server_default=sa.func.now(),nullable=False),
        sa.Column("decided_at",sa.DateTime(timezone=True)),
    )
    for name,col in [("person_id","person_id"),("facility_id","facility_id"),("coverage_id","coverage_id"),("payer_id","payer_id"),("service_code","service_code"),("service_type","service_type"),("status","status")]:
        op.create_index("ix_financing_preauthorizations_"+name,"financing_preauthorizations",[col])

def downgrade():
    for name in ["status","service_type","service_code","payer_id","coverage_id","facility_id","person_id"]:
        op.drop_index("ix_financing_preauthorizations_"+name,table_name="financing_preauthorizations")
    op.drop_table("financing_preauthorizations")
