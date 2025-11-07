"""Add folder hierarchy support to ImageGroup model"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20251107_03'
down_revision = '20251107_02'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add folder hierarchy columns to image_groups table
    op.add_column('image_groups', sa.Column('parent_id', sa.Integer(), nullable=True))
    op.add_column('image_groups', sa.Column('sort_order', sa.Integer(), nullable=False, server_default='0'))

    # Add foreign key constraint for parent_id
    op.create_foreign_key(
        'fk_image_groups_parent_id',
        'image_groups',
        'image_groups',
        ['parent_id'],
        ['id'],
        ondelete='CASCADE'
    )


def downgrade() -> None:
    # Remove foreign key constraint
    op.drop_constraint('fk_image_groups_parent_id', 'image_groups', type_='foreignkey')

    # Remove folder hierarchy columns from image_groups table
    op.drop_column('image_groups', 'sort_order')
    op.drop_column('image_groups', 'parent_id')
