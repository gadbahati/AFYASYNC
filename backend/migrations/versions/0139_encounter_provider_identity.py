"""Phase 176: link encounters to the responsible provider staff member."""
from alembic import op
import sqlalchemy as sa

revision = "0139_encounter_provider_identity"
down_revision = "0138_terminology_permission"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {c["name"] for c in inspector.get_columns("encounters")}
    if "provider_staff_id" not in columns:
        op.add_column(
            "encounters",
            sa.Column(
                "provider_staff_id",
                sa.UUID(),
                sa.ForeignKey("staff.id", ondelete="SET NULL"),
                nullable=True,
            ),
        )
    indexes = {i["name"] for i in inspector.get_indexes("encounters")}
    if "ix_encounters_provider_staff_id" not in indexes:
        op.create_index("ix_encounters_provider_staff_id", "encounters", ["provider_staff_id"])


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    indexes = {i["name"] for i in inspector.get_indexes("encounters")}
    if "ix_encounters_provider_staff_id" in indexes:
        op.drop_index("ix_encounters_provider_staff_id", table_name="encounters")
    columns = {c["name"] for c in inspector.get_columns("encounters")}
    if "provider_staff_id" in columns:
        op.drop_column("encounters", "provider_staff_id")
