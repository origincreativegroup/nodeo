"""Add grouping and collection tables"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import expression

# revision identifiers, used by Alembic.
revision = '20240711_01'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    group_type_enum = sa.Enum(
        'ai_tag_cluster',
        'ai_scene_cluster',
        'ai_embedding_cluster',
        'manual_collection',
        'upload_batch',
        name='grouptype',
    )

    op.create_table(
        'upload_batches',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('label', sa.String(length=255), nullable=False),
        sa.Column('source', sa.String(length=255), nullable=True),
        sa.Column('attributes', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.add_column('images', sa.Column('ai_embedding', sa.JSON(), nullable=True))
    op.add_column('images', sa.Column('upload_batch_id', sa.Integer(), nullable=True))
    op.create_foreign_key(
        'fk_images_upload_batch_id',
        'images',
        'upload_batches',
        ['upload_batch_id'],
        ['id'],
        ondelete='SET NULL',
    )

    group_type_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        'image_groups',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('group_type', group_type_enum, nullable=False),
        sa.Column('attributes', sa.JSON(), nullable=True),
        sa.Column('is_user_defined', sa.Boolean(), nullable=False, server_default=expression.false()),
        sa.Column('created_by', sa.String(length=255), nullable=True),
        sa.Column('upload_batch_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now()),
        sa.ForeignKeyConstraint(['upload_batch_id'], ['upload_batches.id'], ondelete='SET NULL'),
    )

    op.create_table(
        'image_group_associations',
        sa.Column('group_id', sa.Integer(), nullable=False),
        sa.Column('image_id', sa.Integer(), nullable=False),
        sa.Column('attributes', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['group_id'], ['image_groups.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['image_id'], ['images.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('group_id', 'image_id', name='pk_image_group_associations'),
        sa.UniqueConstraint('group_id', 'image_id', name='uq_image_group_assignment'),
    )


def downgrade() -> None:
    op.drop_table('image_group_associations')
    op.drop_table('image_groups')

    op.drop_constraint('fk_images_upload_batch_id', 'images', type_='foreignkey')
    op.drop_column('images', 'upload_batch_id')
    op.drop_column('images', 'ai_embedding')

    op.drop_table('upload_batches')

    sa.Enum(name='grouptype').drop(op.get_bind(), checkfirst=True)
