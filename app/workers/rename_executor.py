"""
Rename executor worker for JSPOW v2

Handles execution of approved rename suggestions with rollback support
"""
import logging
import shutil
from pathlib import Path
from typing import Optional
from uuid import UUID
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal
from app.models import (
    RenameSuggestion,
    SuggestionStatus,
    Image,
    ActivityLog,
    ActivityActionType,
    WatchedFolder,
)

logger = logging.getLogger(__name__)


class RenameExecutor:
    """Executes approved rename operations with rollback support"""

    async def execute_suggestion(
        self,
        suggestion_id: UUID,
        create_backup: bool = True
    ) -> dict:
        """
        Execute an approved rename suggestion

        Args:
            suggestion_id: ID of the suggestion to execute
            create_backup: Whether to create a backup before renaming

        Returns:
            dict with success status and details
        """
        async with AsyncSessionLocal() as db:
            try:
                # Get suggestion
                result = await db.execute(
                    select(RenameSuggestion).where(RenameSuggestion.id == suggestion_id)
                )
                suggestion = result.scalar_one_or_none()

                if not suggestion:
                    return {
                        "success": False,
                        "error": "Suggestion not found"
                    }

                if suggestion.status != SuggestionStatus.APPROVED:
                    return {
                        "success": False,
                        "error": f"Suggestion status is {suggestion.status.value}, not approved"
                    }

                # Get associated image
                if not suggestion.asset_id:
                    return {
                        "success": False,
                        "error": "No asset associated with suggestion"
                    }

                image_result = await db.execute(
                    select(Image).where(Image.id == suggestion.asset_id)
                )
                image = image_result.scalar_one_or_none()

                if not image:
                    return {
                        "success": False,
                        "error": "Associated asset not found"
                    }

                # Perform rename
                old_path = Path(image.file_path)
                new_filename = suggestion.suggested_filename

                # Ensure new filename has correct extension
                if not new_filename.endswith(old_path.suffix):
                    new_filename = new_filename + old_path.suffix

                new_path = old_path.parent / new_filename

                # Check if target already exists
                if new_path.exists() and new_path != old_path:
                    return {
                        "success": False,
                        "error": f"Target file already exists: {new_filename}"
                    }

                # Create backup if requested
                backup_path = None
                if create_backup:
                    backup_path = old_path.parent / f"{old_path.name}.backup"
                    try:
                        shutil.copy2(old_path, backup_path)
                        logger.info(f"Created backup: {backup_path}")
                    except Exception as e:
                        logger.error(f"Error creating backup: {e}")
                        return {
                            "success": False,
                            "error": f"Failed to create backup: {str(e)}"
                        }

                # Perform rename
                try:
                    old_path.rename(new_path)
                    logger.info(f"Renamed {old_path.name} -> {new_filename}")
                except Exception as e:
                    logger.error(f"Error renaming file: {e}")

                    # Restore from backup if it exists
                    if backup_path and backup_path.exists():
                        try:
                            shutil.move(str(backup_path), str(old_path))
                            logger.info("Restored from backup after rename failure")
                        except:
                            pass

                    return {
                        "success": False,
                        "error": f"Failed to rename file: {str(e)}"
                    }

                # Update database
                image.current_filename = new_filename
                image.file_path = str(new_path)

                suggestion.status = SuggestionStatus.APPLIED

                await db.commit()

                # Create activity log
                activity_log = ActivityLog(
                    watched_folder_id=suggestion.watched_folder_id,
                    asset_id=image.id,
                    action_type=ActivityActionType.RENAME,
                    original_filename=suggestion.original_filename,
                    new_filename=new_filename,
                    folder_path=str(new_path.parent),
                    status="success",
                    metadata={
                        "suggestion_id": str(suggestion_id),
                        "backup_created": backup_path is not None,
                        "backup_path": str(backup_path) if backup_path else None,
                    }
                )
                db.add(activity_log)

                # Update folder stats
                if suggestion.watched_folder_id:
                    folder_result = await db.execute(
                        select(WatchedFolder).where(
                            WatchedFolder.id == suggestion.watched_folder_id
                        )
                    )
                    folder = folder_result.scalar_one_or_none()
                    if folder and folder.pending_count > 0:
                        folder.pending_count -= 1

                await db.commit()

                # Clean up backup if rename succeeded
                if backup_path and backup_path.exists():
                    try:
                        backup_path.unlink()
                        logger.info("Removed backup after successful rename")
                    except:
                        pass

                return {
                    "success": True,
                    "old_filename": suggestion.original_filename,
                    "new_filename": new_filename,
                    "asset_id": image.id
                }

            except Exception as e:
                logger.error(f"Error executing suggestion {suggestion_id}: {e}", exc_info=True)

                # Try to create error log
                try:
                    if suggestion:
                        error_log = ActivityLog(
                            watched_folder_id=suggestion.watched_folder_id,
                            asset_id=suggestion.asset_id,
                            action_type=ActivityActionType.ERROR,
                            original_filename=suggestion.original_filename,
                            new_filename=suggestion.suggested_filename,
                            status="failure",
                            error_message=str(e)
                        )
                        db.add(error_log)

                        # Mark suggestion as failed
                        suggestion.status = SuggestionStatus.FAILED
                        await db.commit()
                except:
                    pass

                return {
                    "success": False,
                    "error": str(e)
                }

    async def execute_batch(
        self,
        suggestion_ids: list[UUID],
        create_backups: bool = True
    ) -> dict:
        """
        Execute multiple approved suggestions in batch

        Args:
            suggestion_ids: List of suggestion IDs to execute
            create_backups: Whether to create backups

        Returns:
            dict with results
        """
        results = []
        succeeded = 0
        failed = 0

        for suggestion_id in suggestion_ids:
            result = await self.execute_suggestion(suggestion_id, create_backups)
            results.append({
                "suggestion_id": str(suggestion_id),
                **result
            })

            if result["success"]:
                succeeded += 1
            else:
                failed += 1

        return {
            "total": len(suggestion_ids),
            "succeeded": succeeded,
            "failed": failed,
            "results": results
        }

    async def rollback_rename(
        self,
        activity_log_id: UUID
    ) -> dict:
        """
        Rollback a rename operation using activity log

        Args:
            activity_log_id: ID of the activity log entry for the rename

        Returns:
            dict with success status and details
        """
        async with AsyncSessionLocal() as db:
            try:
                # Get activity log
                result = await db.execute(
                    select(ActivityLog).where(ActivityLog.id == activity_log_id)
                )
                log = result.scalar_one_or_none()

                if not log:
                    return {
                        "success": False,
                        "error": "Activity log not found"
                    }

                if log.action_type != ActivityActionType.RENAME:
                    return {
                        "success": False,
                        "error": "Activity log is not a rename operation"
                    }

                if log.status != "success":
                    return {
                        "success": False,
                        "error": "Cannot rollback failed rename"
                    }

                # Get image
                if not log.asset_id:
                    return {
                        "success": False,
                        "error": "No asset associated with activity log"
                    }

                image_result = await db.execute(
                    select(Image).where(Image.id == log.asset_id)
                )
                image = image_result.scalar_one_or_none()

                if not image:
                    return {
                        "success": False,
                        "error": "Associated asset not found"
                    }

                # Perform rollback rename
                current_path = Path(image.file_path)
                original_filename = log.original_filename

                if not original_filename:
                    return {
                        "success": False,
                        "error": "Original filename not recorded in activity log"
                    }

                rollback_path = current_path.parent / original_filename

                # Check if can rollback
                if rollback_path.exists() and rollback_path != current_path:
                    return {
                        "success": False,
                        "error": f"Cannot rollback: original filename exists: {original_filename}"
                    }

                # Perform rollback
                try:
                    current_path.rename(rollback_path)
                    logger.info(f"Rolled back {current_path.name} -> {original_filename}")
                except Exception as e:
                    logger.error(f"Error during rollback: {e}")
                    return {
                        "success": False,
                        "error": f"Failed to rollback rename: {str(e)}"
                    }

                # Update database
                image.current_filename = original_filename
                image.file_path = str(rollback_path)

                await db.commit()

                # Create activity log for rollback
                rollback_log = ActivityLog(
                    watched_folder_id=log.watched_folder_id,
                    asset_id=image.id,
                    action_type=ActivityActionType.RENAME,
                    original_filename=log.new_filename,
                    new_filename=original_filename,
                    folder_path=str(rollback_path.parent),
                    status="success",
                    metadata={
                        "rollback": True,
                        "original_activity_log_id": str(activity_log_id)
                    }
                )
                db.add(rollback_log)
                await db.commit()

                return {
                    "success": True,
                    "rolled_back_from": log.new_filename,
                    "rolled_back_to": original_filename,
                    "asset_id": image.id
                }

            except Exception as e:
                logger.error(f"Error rolling back activity {activity_log_id}: {e}", exc_info=True)
                return {
                    "success": False,
                    "error": str(e)
                }


# Global rename executor instance
rename_executor = RenameExecutor()
