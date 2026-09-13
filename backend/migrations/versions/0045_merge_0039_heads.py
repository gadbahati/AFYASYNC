"""merge 0039 heads

Revision ID: 0045_merge_0039_heads
Revises: 0039_radiology, 0044_dietetics

Graph-only merge: 0038_wards_beds forked into two branches —
0039_radiology (a short, otherwise-unextended branch) and 0039_theatre,
which continued on through maternity, child_health, blood_bank,
patient_safety and dietetics (0044_dietetics is that chain's current tip).
This converges them back to one head. No schema changes here.
"""

revision = "0045_merge_0039_heads"
down_revision = (
    "0039_radiology",
    "0044_dietetics",
)
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Merge point only; all schema changes live in its ancestor revisions."""


def downgrade() -> None:
    """Merge point only; Alembic downgrades through the ancestor branches."""
