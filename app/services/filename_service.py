"""Filename conflict detection and uniqueness service"""
import logging
from pathlib import Path
from typing import Optional, Dict, List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import Image, ImageGroup

logger = logging.getLogger(__name__)


class FilenameService:
    """Service for managing filename conflicts and ensuring uniqueness"""

    @staticmethod
    async def check_filename_conflict(
        filename: str,
        folder_id: Optional[int],
        db: AsyncSession,
        exclude_image_id: Optional[int] = None
    ) -> bool:
        """
        Check if a filename already exists in a specific folder or globally

        Args:
            filename: The filename to check (with or without extension)
            folder_id: Folder/group ID to check within (None for global check)
            db: Database session
            exclude_image_id: Optional image ID to exclude from check (for renames)

        Returns:
            True if conflict exists, False otherwise
        """
        try:
            # Build query based on folder context
            if folder_id:
                # Check within specific folder
                stmt = (
                    select(Image)
                    .join(Image.groups)
                    .where(
                        ImageGroup.id == folder_id,
                        Image.current_filename == filename
                    )
                )
            else:
                # Global check
                stmt = select(Image).where(Image.current_filename == filename)

            # Exclude specific image if doing rename
            if exclude_image_id:
                stmt = stmt.where(Image.id != exclude_image_id)

            result = await db.execute(stmt)
            existing = result.scalar_one_or_none()

            return existing is not None

        except Exception as e:
            logger.error(f"Error checking filename conflict: {e}")
            return False

    @staticmethod
    async def suggest_unique_name(
        base_name: str,
        extension: str,
        folder_id: Optional[int],
        db: AsyncSession,
        exclude_image_id: Optional[int] = None
    ) -> str:
        """
        Generate a unique filename by adding suffix if conflicts exist

        Args:
            base_name: Base filename without extension
            extension: File extension (e.g., '.jpg')
            folder_id: Folder/group ID to check within
            db: Database session
            exclude_image_id: Optional image ID to exclude from check

        Returns:
            Unique filename with extension
        """
        try:
            # Ensure extension has leading dot
            if not extension.startswith('.'):
                extension = f'.{extension}'

            # Try base name first
            candidate = f"{base_name}{extension}"
            has_conflict = await FilenameService.check_filename_conflict(
                candidate, folder_id, db, exclude_image_id
            )

            if not has_conflict:
                return candidate

            # Add numeric suffix until we find unique name
            counter = 2
            while counter < 1000:  # Safety limit
                candidate = f"{base_name}_{counter}{extension}"
                has_conflict = await FilenameService.check_filename_conflict(
                    candidate, folder_id, db, exclude_image_id
                )

                if not has_conflict:
                    return candidate

                counter += 1

            # Fallback: add timestamp
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            return f"{base_name}_{timestamp}{extension}"

        except Exception as e:
            logger.error(f"Error suggesting unique name: {e}")
            # Fallback with timestamp
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            return f"{base_name}_{timestamp}{extension}"

    @staticmethod
    async def batch_check_conflicts(
        filenames: List[str],
        folder_id: Optional[int],
        db: AsyncSession
    ) -> Dict[str, bool]:
        """
        Check multiple filenames for conflicts in one operation

        Args:
            filenames: List of filenames to check
            folder_id: Folder/group ID to check within
            db: Database session

        Returns:
            Dict mapping filename to conflict status (True if conflict)
        """
        results = {}

        try:
            # Build query for all filenames at once
            if folder_id:
                stmt = (
                    select(Image.current_filename)
                    .join(Image.groups)
                    .where(
                        ImageGroup.id == folder_id,
                        Image.current_filename.in_(filenames)
                    )
                )
            else:
                stmt = select(Image.current_filename).where(
                    Image.current_filename.in_(filenames)
                )

            result = await db.execute(stmt)
            existing_filenames = {row[0] for row in result.all()}

            # Map results
            for filename in filenames:
                results[filename] = filename in existing_filenames

        except Exception as e:
            logger.error(f"Error in batch conflict check: {e}")
            # Fallback: assume no conflicts
            results = {filename: False for filename in filenames}

        return results

    @staticmethod
    def sanitize_filename(filename: str, max_length: int = 100) -> str:
        """
        Sanitize filename to be filesystem-safe

        Args:
            filename: Input filename
            max_length: Maximum filename length (default 100)

        Returns:
            Sanitized filename
        """
        # Remove or replace invalid characters
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            filename = filename.replace(char, '_')

        # Replace multiple underscores with single
        while '__' in filename:
            filename = filename.replace('__', '_')

        # Remove leading/trailing underscores and spaces
        filename = filename.strip('_ ')

        # Truncate if too long
        if len(filename) > max_length:
            # Preserve extension
            path = Path(filename)
            stem = path.stem[:max_length - len(path.suffix)]
            filename = f"{stem}{path.suffix}"

        return filename

    @staticmethod
    async def get_next_index_in_folder(
        folder_id: int,
        db: AsyncSession
    ) -> int:
        """
        Get the next sequential index number for files in a folder

        Args:
            folder_id: Folder/group ID
            db: Database session

        Returns:
            Next available index (1-based)
        """
        try:
            # Count images in folder
            stmt = (
                select(Image)
                .join(Image.groups)
                .where(ImageGroup.id == folder_id)
            )

            result = await db.execute(stmt)
            count = len(result.all())

            return count + 1

        except Exception as e:
            logger.error(f"Error getting next index: {e}")
            return 1


# Global instance
filename_service = FilenameService()
