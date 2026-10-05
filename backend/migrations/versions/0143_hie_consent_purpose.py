"""Normalize HIE consent operations purpose default and legacy typo."""
from alembic import op
import sqlalchemy as sa

revision = "0143_hie_consent_purpose"
down_revision = "0142_clinical_schema_reconciliation"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        sa.text(
            "UPDATE hie_consents SET purpose = 'OPERATIONS' "
            "WHERE upper(trim(purpose)) = 'HOPERAT'"
        )
    )
    op.alter_column(
        "hie_consents",
        "purpose",
        existing_type=sa.String(length=100),
        server_default=sa.text("'OPERATIONS'"),
        existing_nullable=False,
    )


def downgrade():
    op.alter_column(
        "hie_consents",
        "purpose",
        existing_type=sa.String(length=100),
        server_default=sa.text("'HOPERAT'"),
        existing_nullable=False,
    )
