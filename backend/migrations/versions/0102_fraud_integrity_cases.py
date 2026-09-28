"""fraud integrity investigation cases
Revision ID: 0102_fraud_integrity_cases
Revises: 0101_settlement_payment
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
revision="0102_fraud_integrity_cases"
down_revision="0101_settlement_payment"
branch_labels=None
depends_on=None
def upgrade():
    op.create_table("fraud_integrity_cases",
        sa.Column("id",postgresql.UUID(as_uuid=True),primary_key=True),
        sa.Column("case_number",sa.String(80),nullable=False,unique=True),
        sa.Column("facility_id",postgresql.UUID(as_uuid=True),sa.ForeignKey("facilities.id",ondelete="RESTRICT"),nullable=False),
        sa.Column("claim_id",postgresql.UUID(as_uuid=True),sa.ForeignKey("claims.id",ondelete="SET NULL")),
        sa.Column("patient_id",postgresql.UUID(as_uuid=True),sa.ForeignKey("persons.id",ondelete="SET NULL")),
        sa.Column("payer_id",postgresql.UUID(as_uuid=True),sa.ForeignKey("payers.id",ondelete="SET NULL")),
        sa.Column("signal_code",sa.String(80),nullable=False),
        sa.Column("severity",sa.String(20),nullable=False,server_default="MEDIUM"),
        sa.Column("status",sa.String(30),nullable=False,server_default="OPEN"),
        sa.Column("summary",sa.Text(),nullable=False),
        sa.Column("evidence",postgresql.JSONB),
        sa.Column("assigned_to",postgresql.UUID(as_uuid=True),sa.ForeignKey("users.id",ondelete="SET NULL")),
        sa.Column("resolution_note",sa.Text()),
        sa.Column("created_at",sa.DateTime(timezone=True),server_default=sa.func.now()),
        sa.Column("resolved_at",sa.DateTime(timezone=True)))
    for n in ["case_number","facility_id","claim_id","patient_id","payer_id","signal_code","severity","status"]:
        op.create_index("ix_fraud_integrity_cases_"+n,"fraud_integrity_cases",[n])
def downgrade():
    for n in ["status","severity","signal_code","payer_id","patient_id","claim_id","facility_id","case_number"]:
        op.drop_index("ix_fraud_integrity_cases_"+n,table_name="fraud_integrity_cases")
    op.drop_table("fraud_integrity_cases")
