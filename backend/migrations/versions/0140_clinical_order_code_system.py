from alembic import op
import sqlalchemy as sa

revision = "0140_clinical_order_code_system"
down_revision = "0139_encounter_provider_identity"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {c["name"] for c in inspector.get_columns("clinical_orders")}
    if "code_system" not in columns:
        op.add_column("clinical_orders", sa.Column("code_system", sa.String(length=500), nullable=True))


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {c["name"] for c in inspector.get_columns("clinical_orders")}
    if "code_system" in columns:
        op.drop_column("clinical_orders", "code_system")
