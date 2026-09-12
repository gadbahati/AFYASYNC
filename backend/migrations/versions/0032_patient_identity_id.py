"""add protected national ID to patient identity

Revision ID: 0032_patient_identity_id
Revises: 0031_preauthorizations
"""

from alembic import op
import sqlalchemy as sa

revision = "0032_patient_identity_id"
down_revision = "0031_preauthorizations"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("persons", sa.Column("national_id_hash", sa.String(length=64), nullable=True))
    op.create_index("ix_persons_national_id_hash", "persons", ["national_id_hash"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_persons_national_id_hash", table_name="persons")
    op.drop_column("persons", "national_id_hash")
