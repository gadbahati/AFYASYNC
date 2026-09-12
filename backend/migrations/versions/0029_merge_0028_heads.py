"""merge 0028 heads

Revision ID: 0029_merge_0028_heads
Revises: 0028_refresh_sessions, 0028_reports_permission

Graph-only merge: 0028_refresh_sessions and 0028_reports_permission were
built in parallel and both forked from 0027_merge_migration_heads, leaving
two heads. This converges them back to one so `alembic upgrade head`
resolves unambiguously. No schema changes here.
"""

revision = "0029_merge_0028_heads"
down_revision = (
    "0028_refresh_sessions",
    "0028_reports_permission",
)
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Merge point only; all schema changes live in its ancestor revisions."""


def downgrade() -> None:
    """Merge point only; Alembic downgrades through the ancestor branches."""
