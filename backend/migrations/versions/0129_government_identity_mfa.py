"""Phase 131 security foundation — Government identity MFA."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0129_government_identity_mfa"
down_revision = "0128_diagnoses_procedures_notes"
branch_labels = None
depends_on = None


def _column_exists(bind, table, column):
    return any(c["name"] == column for c in sa.inspect(bind).get_columns(table))


def _table_exists(bind, name):
    return sa.inspect(bind).has_table(name)


def upgrade():
    bind = op.get_bind()

    if not _column_exists(bind, "users", "mfa_required"):
        op.add_column("users", sa.Column("mfa_required", sa.Boolean(), nullable=False, server_default=sa.text("false")))
    if not _column_exists(bind, "users", "mfa_secret_encrypted"):
        op.add_column("users", sa.Column("mfa_secret_encrypted", sa.Text(), nullable=True))
    if not _column_exists(bind, "users", "mfa_enrolled_at"):
        op.add_column("users", sa.Column("mfa_enrolled_at", sa.DateTime(timezone=True), nullable=True))
    if not _column_exists(bind, "users", "mfa_last_verified_at"):
        op.add_column("users", sa.Column("mfa_last_verified_at", sa.DateTime(timezone=True), nullable=True))

    if not _table_exists(bind, "mfa_challenges"):
        op.create_table(
            "mfa_challenges",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("portal_type", sa.String(30), nullable=False, server_default="government"),
            sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("status", sa.String(20), nullable=False, server_default="PENDING"),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="SET NULL"),
        )
        op.create_index("ix_mfa_challenges_user_status", "mfa_challenges", ["user_id", "status"])
        op.create_index("ix_mfa_challenges_expires_at", "mfa_challenges", ["expires_at"])


def downgrade():
    bind = op.get_bind()
    if _table_exists(bind, "mfa_challenges"):
        op.drop_index("ix_mfa_challenges_expires_at", table_name="mfa_challenges")
        op.drop_index("ix_mfa_challenges_user_status", table_name="mfa_challenges")
        op.drop_table("mfa_challenges")
    for column in ("mfa_last_verified_at", "mfa_enrolled_at", "mfa_secret_encrypted", "mfa_required"):
        if _column_exists(bind, "users", column):
            op.drop_column("users", column)
