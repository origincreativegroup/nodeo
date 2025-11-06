"""Add missing columns to images table

Revision ID: 20251106_02
Revises: 20251106_01
Create Date: 2025-11-06 12:20:00
"""

async def upgrade(conn):
    """Add missing columns to images table"""

    # Create media_type enum if it doesn't exist
    await conn.execute("""
        DO $$ BEGIN
            CREATE TYPE mediatype AS ENUM ('IMAGE', 'VIDEO');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """)

    # Add media_type column
    await conn.execute("""
        ALTER TABLE images
        ADD COLUMN IF NOT EXISTS media_type mediatype DEFAULT 'IMAGE' NOT NULL;
    """)

    # Add video metadata columns
    await conn.execute("""
        ALTER TABLE images
        ADD COLUMN IF NOT EXISTS duration_s FLOAT,
        ADD COLUMN IF NOT EXISTS frame_rate FLOAT,
        ADD COLUMN IF NOT EXISTS codec VARCHAR(100),
        ADD COLUMN IF NOT EXISTS media_format VARCHAR(100);
    """)

    # Add AI embedding column
    await conn.execute("""
        ALTER TABLE images
        ADD COLUMN IF NOT EXISTS ai_embedding JSON;
    """)

    # Add metadata_id foreign key
    await conn.execute("""
        ALTER TABLE images
        ADD COLUMN IF NOT EXISTS metadata_id INTEGER REFERENCES media_metadata(id);
    """)

    # Add upload_batch_id foreign key (if upload_batches table exists)
    await conn.execute("""
        ALTER TABLE images
        ADD COLUMN IF NOT EXISTS upload_batch_id INTEGER REFERENCES upload_batches(id) ON DELETE SET NULL;
    """)

    # Add project_id foreign key (if projects table exists)
    await conn.execute("""
        ALTER TABLE images
        ADD COLUMN IF NOT EXISTS project_id INTEGER REFERENCES projects(id) ON DELETE SET NULL;
    """)


async def downgrade(conn):
    """Remove added columns"""
    await conn.execute("""
        ALTER TABLE images
        DROP COLUMN IF EXISTS project_id,
        DROP COLUMN IF EXISTS upload_batch_id,
        DROP COLUMN IF EXISTS metadata_id,
        DROP COLUMN IF EXISTS ai_embedding,
        DROP COLUMN IF EXISTS media_format,
        DROP COLUMN IF EXISTS codec,
        DROP COLUMN IF EXISTS frame_rate,
        DROP COLUMN IF EXISTS duration_s,
        DROP COLUMN IF EXISTS media_type;
    """)

    await conn.execute("""
        DROP TYPE IF EXISTS mediatype;
    """)
