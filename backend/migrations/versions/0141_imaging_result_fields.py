"""Phase 182 — persist structured imaging result fields."""
from alembic import op
import sqlalchemy as sa

revision = "0141_imaging_result_fields"
down_revision = "0140_clinical_order_code_system"
branch_labels = None
depends_on = None

def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    cols = {c["name"] for c in inspector.get_columns("clinical_orders")}
    if "modality" not in cols:
        op.add_column("clinical_orders", sa.Column("modality", sa.String(length=100), nullable=True))
    if "impression" not in cols:
        op.add_column("clinical_orders", sa.Column("impression", sa.Text(), nullable=True))

def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    cols = {c["name"] for c in inspector.get_columns("clinical_orders")}
    if "impression" in cols:
        op.drop_column("clinical_orders", "impression")
    if "modality" in cols:
        op.drop_column("clinical_orders", "modality")
