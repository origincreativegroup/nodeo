"""Enhance template model with favorite, category, and usage tracking"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '20251107_01'
down_revision = '20251106_02'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add new columns to templates table
    op.add_column('templates', sa.Column('is_favorite', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('templates', sa.Column('category', sa.String(length=50), nullable=False, server_default='custom'))
    op.add_column('templates', sa.Column('usage_count', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('templates', sa.Column('variables_used', sa.JSON(), nullable=True))


def downgrade() -> None:
    # Remove columns from templates table
    op.drop_column('templates', 'variables_used')
    op.drop_column('templates', 'usage_count')
    op.drop_column('templates', 'category')
    op.drop_column('templates', 'is_favorite')
