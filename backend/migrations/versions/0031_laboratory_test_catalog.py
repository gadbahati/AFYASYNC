"""add laboratory test catalog description and pricing

Revision ID: 0031_laboratory_test_catalog
Revises: 0030_admissions
"""

from alembic import op
import sqlalchemy as sa

revision = "0031_laboratory_test_catalog"
down_revision = "0030_admissions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("lab_tests", sa.Column("description", sa.Text(), nullable=True))
    op.add_column("lab_tests", sa.Column("price", sa.Numeric(14, 2), nullable=True))
    op.execute("UPDATE lab_tests SET price = 0 WHERE price IS NULL")
    op.alter_column("lab_tests", "price", nullable=False, server_default=sa.text("0"))


def downgrade() -> None:
    op.drop_column("lab_tests", "price")
    op.drop_column("lab_tests", "description")
