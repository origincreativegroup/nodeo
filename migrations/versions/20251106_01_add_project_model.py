"""Add project model and project relationships"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import expression

# revision identifiers, used by Alembic.
revision = '20251106_01'
down_revision = '20240711_01'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create ProjectType enum
    project_type_enum = sa.Enum(
        'client',
        'personal',
        'commercial',
        'stock',
        'exhibition',
        'experimental',
        name='projecttype',
    )
    project_type_enum.create(op.get_bind(), checkfirst=True)

    # Create projects table
    op.create_table(
        'projects',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('name', sa.String(length=255), nullable=False, unique=True),
        sa.Column('slug', sa.String(length=255), nullable=False, unique=True, index=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('project_type', project_type_enum, nullable=False, server_default='personal'),
        sa.Column('ai_keywords', sa.JSON(), nullable=True),
        sa.Column('visual_themes', sa.JSON(), nullable=True),
        sa.Column('start_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('end_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('nextcloud_folder', sa.String(length=500), nullable=True),
        sa.Column('default_naming_template', sa.String(length=500), nullable=True),
        sa.Column('portfolio_metadata', sa.JSON(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=expression.true()),
        sa.Column('featured_on_portfolio', sa.Boolean(), nullable=False, server_default=expression.false()),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now()),
    )

    # Add project_id to images table
    op.add_column('images', sa.Column('project_id', sa.Integer(), nullable=True))
    op.create_foreign_key(
        'fk_images_project_id',
        'images',
        'projects',
        ['project_id'],
        ['id'],
        ondelete='SET NULL',
    )

    # Add project_id to image_groups table
    op.add_column('image_groups', sa.Column('project_id', sa.Integer(), nullable=True))
    op.create_foreign_key(
        'fk_image_groups_project_id',
        'image_groups',
        'projects',
        ['project_id'],
        ['id'],
        ondelete='SET NULL',
    )

    # Update GroupType enum to include AI_PROJECT_CLUSTER
    # Note: PostgreSQL enum update requires special handling
    op.execute("ALTER TYPE grouptype ADD VALUE IF NOT EXISTS 'ai_project_cluster'")


def downgrade() -> None:
    # Remove project_id from image_groups
    op.drop_constraint('fk_image_groups_project_id', 'image_groups', type_='foreignkey')
    op.drop_column('image_groups', 'project_id')

    # Remove project_id from images
    op.drop_constraint('fk_images_project_id', 'images', type_='foreignkey')
    op.drop_column('images', 'project_id')

    # Drop projects table
    op.drop_table('projects')

    # Drop ProjectType enum
    sa.Enum(name='projecttype').drop(op.get_bind(), checkfirst=True)

    # Note: Removing 'ai_project_cluster' from GroupType enum is complex in PostgreSQL
    # and not included here to avoid potential data issues
