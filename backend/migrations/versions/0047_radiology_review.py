"""add radiology report review fields
Revision ID: 0047_radiology_review
Revises: 0046_merge_heads
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
revision="0047_radiology_review";down_revision="0046_merge_heads";branch_labels=None;depends_on=None

def upgrade():
    op.add_column("imaging_reports",sa.Column("reviewed_by",postgresql.UUID(as_uuid=True),sa.ForeignKey("staff.id",ondelete="RESTRICT")))
    op.add_column("imaging_reports",sa.Column("reviewed_at",sa.DateTime(timezone=True)))
    op.add_column("imaging_reports",sa.Column("report_status",sa.String(30),nullable=False,server_default="FINAL"))

def downgrade():
    op.drop_column("imaging_reports","report_status")
    op.drop_column("imaging_reports","reviewed_at")
    op.drop_column("imaging_reports","reviewed_by")
