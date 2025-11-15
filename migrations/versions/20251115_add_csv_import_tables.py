"""Add CSV import tables for bulk asset upload

Revision ID: 20251115_csv_import
Revises: 20251113_v2_tables
Create Date: 2025-11-15 00:00:00.000000+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '20251115_csv_import'
down_revision: Union[str, None] = '20251113_v2_tables'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create CSV import status enum
    op.execute("""
        CREATE TYPE csvimportstatus AS ENUM (
            'PENDING',
            'PROCESSING',
            'COMPLETED',
            'FAILED',
            'PARTIALLY_COMPLETED'
        )
    """)

    # Create CSV import row status enum
    op.execute("""
        CREATE TYPE csvimportrowstatus AS ENUM (
            'PENDING',
            'MATCHED',
            'NOT_FOUND',
            'ERROR'
        )
    """)

    # Create csv_imports table
    op.create_table(
        'csv_imports',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('filename', sa.String(length=500), nullable=False),
        sa.Column('file_path', sa.String(length=1000), nullable=False),
        sa.Column('status', sa.Enum('PENDING', 'PROCESSING', 'COMPLETED', 'FAILED', 'PARTIALLY_COMPLETED', name='csvimportstatus'), nullable=False),
        sa.Column('total_rows', sa.Integer(), nullable=True),
        sa.Column('processed_rows', sa.Integer(), nullable=True),
        sa.Column('matched_rows', sa.Integer(), nullable=True),
        sa.Column('failed_rows', sa.Integer(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )

    # Create csv_import_rows table
    op.create_table(
        'csv_import_rows',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('csv_import_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('row_number', sa.Integer(), nullable=False),
        sa.Column('status', sa.Enum('PENDING', 'MATCHED', 'NOT_FOUND', 'ERROR', name='csvimportrowstatus'), nullable=False),
        sa.Column('priority', sa.String(length=50), nullable=True),
        sa.Column('category', sa.String(length=255), nullable=True),
        sa.Column('page_component', sa.String(length=255), nullable=True),
        sa.Column('asset_name', sa.String(length=500), nullable=True),
        sa.Column('file_path', sa.String(length=1000), nullable=True),
        sa.Column('dimensions', sa.String(length=100), nullable=True),
        sa.Column('format', sa.String(length=50), nullable=True),
        sa.Column('file_size_target', sa.String(length=100), nullable=True),
        sa.Column('csv_status', sa.String(length=100), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('matched_asset_id', sa.Integer(), nullable=True),
        sa.Column('match_score', sa.Float(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('processed_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['csv_import_id'], ['csv_imports.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['matched_asset_id'], ['images.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )

    # Create indexes for performance
    op.create_index(op.f('ix_csv_imports_status'), 'csv_imports', ['status'], unique=False)
    op.create_index(op.f('ix_csv_imports_created_at'), 'csv_imports', ['created_at'], unique=False)
    op.create_index(op.f('ix_csv_import_rows_csv_import_id'), 'csv_import_rows', ['csv_import_id'], unique=False)
    op.create_index(op.f('ix_csv_import_rows_status'), 'csv_import_rows', ['status'], unique=False)
    op.create_index(op.f('ix_csv_import_rows_matched_asset_id'), 'csv_import_rows', ['matched_asset_id'], unique=False)


def downgrade() -> None:
    # Drop indexes
    op.drop_index(op.f('ix_csv_import_rows_matched_asset_id'), table_name='csv_import_rows')
    op.drop_index(op.f('ix_csv_import_rows_status'), table_name='csv_import_rows')
    op.drop_index(op.f('ix_csv_import_rows_csv_import_id'), table_name='csv_import_rows')
    op.drop_index(op.f('ix_csv_imports_created_at'), table_name='csv_imports')
    op.drop_index(op.f('ix_csv_imports_status'), table_name='csv_imports')

    # Drop tables
    op.drop_table('csv_import_rows')
    op.drop_table('csv_imports')

    # Drop enums
    op.execute('DROP TYPE IF EXISTS csvimportrowstatus')
    op.execute('DROP TYPE IF EXISTS csvimportstatus')
