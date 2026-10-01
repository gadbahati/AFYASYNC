from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
revision='0108_benefit_engine'
down_revision='0107_referral_booking'
branch_labels=None
depends_on=None

def upgrade():
    op.create_table('benefit_rule_versions',
        sa.Column('id',postgresql.UUID(as_uuid=True),primary_key=True),
        sa.Column('benefit_package_id',postgresql.UUID(as_uuid=True),sa.ForeignKey('benefit_packages.id',ondelete='RESTRICT'),nullable=False),
        sa.Column('payer_id',postgresql.UUID(as_uuid=True),sa.ForeignKey('payers.id',ondelete='RESTRICT'),nullable=False),
        sa.Column('payer_plan_id',postgresql.UUID(as_uuid=True),sa.ForeignKey('payer_plans.id',ondelete='RESTRICT')),
        sa.Column('name',sa.String(160),nullable=False),sa.Column('version',sa.Integer(),nullable=False,server_default='1'),
        sa.Column('service_code',sa.String(80)),sa.Column('service_type',sa.String(60)),
        sa.Column('tariff_amount',sa.Numeric(14,2)),sa.Column('currency',sa.String(3),nullable=False,server_default='KES'),
        sa.Column('payer_percent',sa.Numeric(5,2),nullable=False,server_default='100'),sa.Column('fixed_patient_copay',sa.Numeric(14,2),nullable=False,server_default='0'),
        sa.Column('max_covered_amount',sa.Numeric(14,2)),sa.Column('annual_limit_amount',sa.Numeric(14,2)),
        sa.Column('is_excluded',sa.Boolean(),nullable=False,server_default=sa.false()),sa.Column('requires_preauth',sa.Boolean(),nullable=False,server_default=sa.false()),
        sa.Column('effective_from',sa.Date(),nullable=False),sa.Column('effective_to',sa.Date()),sa.Column('status',sa.String(30),nullable=False,server_default='DRAFT'),sa.Column('created_at',sa.DateTime(timezone=True),server_default=sa.func.now(),nullable=False))

def downgrade():
    op.drop_table('benefit_rule_versions')
