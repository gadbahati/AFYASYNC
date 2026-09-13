"""merge the two 0045 migration heads
Revision ID: 0046_merge_heads
Revises: 0045_merge_0039_heads, 0045_infection_control
"""
revision="0046_merge_heads"
down_revision=("0045_merge_0039_heads","0045_infection_control")
branch_labels=None
depends_on=None

def upgrade():
    pass

def downgrade():
    pass
