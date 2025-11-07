#!/usr/bin/env python3
"""
Run database migrations manually
"""
import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from app.database import engine
from app.config import settings
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def run_migration(migration_file: Path):
    """Run a single migration file"""
    try:
        logger.info(f"Running migration: {migration_file.name}")

        # Import the migration module
        import importlib.util
        spec = importlib.util.spec_from_file_location("migration", migration_file)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        # Execute the upgrade function
        async with engine.begin() as conn:
            await conn.run_sync(module.upgrade)

        logger.info(f"✓ Migration {migration_file.name} completed successfully")
        return True

    except Exception as e:
        logger.error(f"✗ Migration {migration_file.name} failed: {e}")
        return False


async def run_all_migrations():
    """Run all pending migrations"""
    migrations_dir = Path(__file__).parent / "migrations" / "versions"

    if not migrations_dir.exists():
        logger.error(f"Migrations directory not found: {migrations_dir}")
        return False

    # Get all migration files
    migration_files = sorted(migrations_dir.glob("*.py"))
    migration_files = [f for f in migration_files if f.name != "__init__.py"]

    if not migration_files:
        logger.info("No migrations found")
        return True

    logger.info(f"Found {len(migration_files)} migration files")
    logger.info(f"Database URL: {settings.database_url}")
    logger.info("=" * 60)

    # Run each migration
    all_success = True
    for migration_file in migration_files:
        success = await run_migration(migration_file)
        if not success:
            all_success = False
            logger.warning("Migration failed, stopping...")
            break

    logger.info("=" * 60)
    if all_success:
        logger.info("✓ All migrations completed successfully!")
    else:
        logger.error("✗ Some migrations failed")

    return all_success


if __name__ == "__main__":
    try:
        success = asyncio.run(run_all_migrations())
        sys.exit(0 if success else 1)
    except Exception as e:
        logger.error(f"Error running migrations: {e}")
        sys.exit(1)
