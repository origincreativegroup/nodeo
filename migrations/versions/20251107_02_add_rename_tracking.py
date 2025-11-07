"""Add rename tracking fields to Image model"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20251107_02'
down_revision = '20251107_01'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add rename tracking columns to images table
    op.add_column('images', sa.Column('suggested_filename', sa.String(length=500), nullable=True))
    op.add_column('images', sa.Column('filename_accepted', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('images', sa.Column('last_renamed_at', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    # Remove rename tracking columns from images table
    op.drop_column('images', 'last_renamed_at')
    op.drop_column('images', 'filename_accepted')
    op.drop_column('images', 'suggested_filename')
