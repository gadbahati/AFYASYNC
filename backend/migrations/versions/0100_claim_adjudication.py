"""independent claims adjudication

Revision ID: 0100_claim_adjudication
Revises: 0099_financing_preauth
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision="0100_claim_adjudication"
down_revision="0099_financing_preauth"
branch_labels=None
depends_on=None

def upgrade():
    op.create_table(
        "claim_adjudications",
        sa.Column("id",postgresql.UUID(as_uuid=True),primary_key=True),
        sa.Column("claim_id",postgresql.UUID(as_uuid=True),nullable=False,unique=True),
        sa.Column("decision",sa.String(40),nullable=False),
        sa.Column("submitted_amount",sa.Numeric(14,2),nullable=False),
        sa.Column("allowed_amount",sa.Numeric(14,2),nullable=False),
        sa.Column("patient_amount",sa.Numeric(14,2),nullable=False),
        sa.Column("reason_code",sa.String(100),nullable=False),
        sa.Column("evidence",postgresql.JSONB),
        sa.Column("adjudicated_at",sa.DateTime(timezone=True),server_default=sa.func.now(),nullable=False),
        sa.Column("adjudicated_by",postgresql.UUID(as_uuid=True),nullable=True),
    )
    op.create_index("ix_claim_adjudications_claim_id","claim_adjudications",["claim_id"])
    op.create_index("ix_claim_adjudications_decision","claim_adjudications",["decision"])
    op.create_table(
        "claim_line_adjudications",
        sa.Column("id",postgresql.UUID(as_uuid=True),primary_key=True),
        sa.Column("adjudication_id",postgresql.UUID(as_uuid=True),nullable=False,sa.ForeignKey("claim_adjudications.id",ondelete="CASCADE")),
        sa.Column("claim_item_id",postgresql.UUID(as_uuid=True),nullable=False),
        sa.Column("submitted_amount",sa.Numeric(14,2),nullable=False),
        sa.Column("allowed_amount",sa.Numeric(14,2),nullable=False),
        sa.Column("decision",sa.String(40),nullable=False),
        sa.Column("reason_code",sa.String(100),nullable=False),
        sa.Column("evidence",postgresql.JSONB),
    )
    op.create_index("ix_claim_line_adjudications_adjudication_id","claim_line_adjudications",["adjudication_id"])
    op.create_index("ix_claim_line_adjudications_claim_item_id","claim_line_adjudications",["claim_item_id"])

def downgrade():
    op.drop_index("ix_claim_line_adjudications_claim_item_id",table_name="claim_line_adjudications")
    op.drop_index("ix_claim_line_adjudications_adjudication_id",table_name="claim_line_adjudications")
    op.drop_table("claim_line_adjudications")
    op.drop_index("ix_claim_adjudications_decision",table_name="claim_adjudications")
    op.drop_index("ix_claim_adjudications_claim_id",table_name="claim_adjudications")
    op.drop_table("claim_adjudications")
