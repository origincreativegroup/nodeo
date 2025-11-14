"""Add JSPOW v2 tables for folder monitoring

Revision ID: 20251113_v2_tables
Revises: ce082c6033de
Create Date: 2025-11-13 00:00:00.000000+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '20251113_v2_tables'
down_revision: Union[str, None] = 'ce082c6033de'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create watched_folders table
    op.create_table(
        'watched_folders',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('path', sa.Text(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('status', sa.Enum('ACTIVE', 'PAUSED', 'ERROR', 'SCANNING', name='watchedfolderstatus'), nullable=False),
        sa.Column('file_count', sa.Integer(), nullable=True),
        sa.Column('analyzed_count', sa.Integer(), nullable=True),
        sa.Column('pending_count', sa.Integer(), nullable=True),
        sa.Column('last_scan_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('path')
    )

    # Create tags table
    op.create_table(
        'tags',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('tag_type', sa.Enum('AI', 'MANUAL', 'SYSTEM', name='tagtype'), nullable=False),
        sa.Column('usage_count', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name')
    )

    # Create rename_suggestions table
    op.create_table(
        'rename_suggestions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('watched_folder_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('asset_id', sa.Integer(), nullable=True),
        sa.Column('original_path', sa.Text(), nullable=False),
        sa.Column('original_filename', sa.String(length=500), nullable=False),
        sa.Column('suggested_filename', sa.String(length=500), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('confidence_score', sa.Float(), nullable=True),
        sa.Column('status', sa.Enum('PENDING', 'APPROVED', 'REJECTED', 'APPLIED', 'FAILED', name='suggestionstatus'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['asset_id'], ['images.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['watched_folder_id'], ['watched_folders.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # Create activity_log table
    op.create_table(
        'activity_log',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('watched_folder_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('asset_id', sa.Integer(), nullable=True),
        sa.Column('action_type', sa.Enum('RENAME', 'APPROVE', 'REJECT', 'SCAN', 'ERROR', 'FOLDER_ADDED', 'FOLDER_REMOVED', name='activityactiontype'), nullable=False),
        sa.Column('original_filename', sa.String(length=500), nullable=True),
        sa.Column('new_filename', sa.String(length=500), nullable=True),
        sa.Column('folder_path', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['asset_id'], ['images.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['watched_folder_id'], ['watched_folders.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )

    # Create asset_tags table
    op.create_table(
        'asset_tags',
        sa.Column('asset_id', sa.Integer(), nullable=False),
        sa.Column('tag_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('confidence', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['asset_id'], ['images.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['tag_id'], ['tags.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('asset_id', 'tag_id')
    )

    # Create indexes for performance
    op.create_index(op.f('ix_rename_suggestions_status'), 'rename_suggestions', ['status'], unique=False)
    op.create_index(op.f('ix_rename_suggestions_watched_folder_id'), 'rename_suggestions', ['watched_folder_id'], unique=False)
    op.create_index(op.f('ix_activity_log_action_type'), 'activity_log', ['action_type'], unique=False)
    op.create_index(op.f('ix_activity_log_created_at'), 'activity_log', ['created_at'], unique=False)


def downgrade() -> None:
    # Drop indexes
    op.drop_index(op.f('ix_activity_log_created_at'), table_name='activity_log')
    op.drop_index(op.f('ix_activity_log_action_type'), table_name='activity_log')
    op.drop_index(op.f('ix_rename_suggestions_watched_folder_id'), table_name='rename_suggestions')
    op.drop_index(op.f('ix_rename_suggestions_status'), table_name='rename_suggestions')

    # Drop tables
    op.drop_table('asset_tags')
    op.drop_table('activity_log')
    op.drop_table('rename_suggestions')
    op.drop_table('tags')
    op.drop_table('watched_folders')

    # Drop enums
    op.execute('DROP TYPE IF EXISTS watchedfolderstatus')
    op.execute('DROP TYPE IF EXISTS suggestionstatus')
    op.execute('DROP TYPE IF EXISTS activityactiontype')
    op.execute('DROP TYPE IF EXISTS tagtype')
