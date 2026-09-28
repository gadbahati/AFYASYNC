from alembic import op
import sqlalchemy as sa
revision = "0100_claim_adjudication"
down_revision = "0099_financing_preauth"
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        "claim_adjudications",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("claim_id", sa.UUID(), nullable=False, unique=True),
        sa.Column("decision", sa.String(40), nullable=False),
        sa.Column("submitted_amount", sa.Numeric(14,2), nullable=False),
        sa.Column("allowed_amount", sa.Numeric(14,2), nullable=False),
        sa.Column("patient_amount", sa.Numeric(14,2), nullable=False),
        sa.Column("reason_code", sa.String(100), nullable=False),
        sa.Column("evidence", sa.JSON()),
        sa.Column("adjudicated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("adjudicated_by", sa.UUID(), nullable=True),
    )
    op.create_table(
        "claim_line_adjudications",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("adjudication_id", sa.UUID(), nullable=False),
        sa.Column("claim_item_id", sa.UUID(), nullable=False),
        sa.Column("submitted_amount", sa.Numeric(14,2), nullable=False),
        sa.Column("allowed_amount", sa.Numeric(14,2), nullable=False),
        sa.Column("decision", sa.String(40), nullable=False),
        sa.Column("reason_code", sa.String(100), nullable=False),
        sa.Column("evidence", sa.JSON()),
    )

def downgrade():
    op.drop_table("claim_line_adjudications")
    op.drop_table("claim_adjudications")
