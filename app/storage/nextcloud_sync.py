"""Nextcloud synchronization service with project-aware organization"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import settings
from app.models import Image, Project, StorageType
from app.storage.nextcloud import NextcloudClient

logger = logging.getLogger(__name__)


@dataclass
class SyncResult:
    """Result of a sync operation"""

    success: bool
    image_id: int
    local_path: str
    nextcloud_path: Optional[str] = None
    error: Optional[str] = None
    bytes_transferred: int = 0


@dataclass
class ProjectSyncResult:
    """Result of syncing an entire project"""

    project_id: int
    project_name: str
    total_assets: int
    synced: int
    failed: int
    skipped: int
    results: List[SyncResult]


class NextcloudSyncService:
    """Service for automatic Nextcloud synchronization"""

    def __init__(
        self,
        db: AsyncSession,
        nextcloud_client: Optional[NextcloudClient] = None,
        auto_sync: bool = None,
    ):
        """
        Initialize Nextcloud sync service

        Args:
            db: Database session
            nextcloud_client: Nextcloud client (uses default if None)
            auto_sync: Enable auto-sync (uses settings.nextcloud_auto_sync if None)
        """
        self.db = db
        self.nextcloud_client = nextcloud_client or NextcloudClient()
        self.auto_sync = (
            auto_sync if auto_sync is not None else settings.nextcloud_auto_sync
        )

    def _get_project_folder_structure(self, project: Project) -> Dict[str, str]:
        """
        Get Nextcloud folder paths for a project

        Args:
            project: Project to get folders for

        Returns:
            Dictionary with folder paths for originals, exports, metadata
        """
        base_folder = project.nextcloud_folder or f"projects/{project.slug}"

        return {
            "base": base_folder,
            "originals": f"{base_folder}/originals",
            "exports": f"{base_folder}/exports",
            "metadata": f"{base_folder}/metadata",
        }

    async def sync_image_to_project(
        self,
        image: Image,
        project: Project,
        force: bool = False,
    ) -> SyncResult:
        """
        Sync a single image to its project folder in Nextcloud

        Args:
            image: Image to sync
            project: Project to sync to
            force: Force re-sync even if already synced

        Returns:
            Sync result
        """
        # Skip if already synced and not forcing
        if not force and image.nextcloud_path and image.storage_type == StorageType.NEXTCLOUD:
            return SyncResult(
                success=True,
                image_id=image.id,
                local_path=image.file_path,
                nextcloud_path=image.nextcloud_path,
                error="Already synced (skipped)",
            )

        # Check if local file exists
        local_path = Path(image.file_path)
        if not local_path.exists():
            return SyncResult(
                success=False,
                image_id=image.id,
                local_path=image.file_path,
                error="Local file not found",
            )

        try:
            # Get project folder structure
            folders = self._get_project_folder_structure(project)

            # Determine which folder to use (originals for now)
            remote_folder = folders["originals"]

            # Build remote path
            remote_filename = image.current_filename
            remote_path = f"{remote_folder}/{remote_filename}"

            # Upload to Nextcloud
            logger.info(f"Syncing image {image.id} to Nextcloud: {remote_path}")
            upload_result = await self.nextcloud_client.upload_file(
                local_path=str(local_path),
                remote_path=remote_path,
                create_parents=True,
            )

            if upload_result["success"]:
                # Update image record
                image.nextcloud_path = upload_result["remote_path"]
                image.storage_type = StorageType.NEXTCLOUD
                await self.db.flush()

                return SyncResult(
                    success=True,
                    image_id=image.id,
                    local_path=image.file_path,
                    nextcloud_path=upload_result["remote_path"],
                    bytes_transferred=upload_result.get("size", 0),
                )
            else:
                return SyncResult(
                    success=False,
                    image_id=image.id,
                    local_path=image.file_path,
                    error=upload_result.get("error", "Upload failed"),
                )

        except Exception as e:
            logger.error(f"Error syncing image {image.id}: {e}")
            return SyncResult(
                success=False,
                image_id=image.id,
                local_path=image.file_path,
                error=str(e),
            )

    async def sync_project(
        self,
        project_id: int,
        force: bool = False,
    ) -> ProjectSyncResult:
        """
        Sync all images in a project to Nextcloud

        Args:
            project_id: Project ID
            force: Force re-sync of already synced images

        Returns:
            Project sync result
        """
        # Load project with images
        result = await self.db.execute(
            select(Project)
            .options(selectinload(Project.images))
            .where(Project.id == project_id)
        )
        project = result.scalar_one_or_none()

        if not project:
            raise ValueError(f"Project {project_id} not found")

        # Sync each image
        results: List[SyncResult] = []
        synced = 0
        failed = 0
        skipped = 0

        for image in project.images:
            sync_result = await self.sync_image_to_project(
                image=image,
                project=project,
                force=force,
            )
            results.append(sync_result)

            if sync_result.success:
                if "skipped" in (sync_result.error or "").lower():
                    skipped += 1
                else:
                    synced += 1
            else:
                failed += 1

        await self.db.commit()

        return ProjectSyncResult(
            project_id=project.id,
            project_name=project.name,
            total_assets=len(project.images),
            synced=synced,
            failed=failed,
            skipped=skipped,
            results=results,
        )

    async def sync_image_on_assignment(
        self,
        image_id: int,
        project_id: int,
    ) -> Optional[SyncResult]:
        """
        Automatically sync an image when assigned to a project

        Args:
            image_id: Image ID
            project_id: Project ID

        Returns:
            Sync result if auto-sync is enabled, None otherwise
        """
        if not self.auto_sync:
            logger.debug("Auto-sync disabled, skipping")
            return None

        # Load image and project
        image_result = await self.db.execute(
            select(Image).where(Image.id == image_id)
        )
        image = image_result.scalar_one_or_none()

        project_result = await self.db.execute(
            select(Project).where(Project.id == project_id)
        )
        project = project_result.scalar_one_or_none()

        if not image or not project:
            logger.warning(f"Image {image_id} or project {project_id} not found")
            return None

        # Sync to Nextcloud
        sync_result = await self.sync_image_to_project(
            image=image,
            project=project,
            force=False,
        )

        await self.db.commit()

        return sync_result

    async def sync_batch(
        self,
        image_ids: List[int],
        force: bool = False,
    ) -> List[SyncResult]:
        """
        Sync multiple images at once

        Args:
            image_ids: List of image IDs to sync
            force: Force re-sync of already synced images

        Returns:
            List of sync results
        """
        results: List[SyncResult] = []

        for image_id in image_ids:
            # Load image with project
            result = await self.db.execute(
                select(Image)
                .options(selectinload(Image.project))
                .where(Image.id == image_id)
            )
            image = result.scalar_one_or_none()

            if not image:
                results.append(
                    SyncResult(
                        success=False,
                        image_id=image_id,
                        local_path="",
                        error="Image not found",
                    )
                )
                continue

            if not image.project:
                results.append(
                    SyncResult(
                        success=False,
                        image_id=image_id,
                        local_path=image.file_path,
                        error="No project assigned",
                    )
                )
                continue

            # Sync to project
            sync_result = await self.sync_image_to_project(
                image=image,
                project=image.project,
                force=force,
            )
            results.append(sync_result)

        await self.db.commit()

        return results

    async def import_from_nextcloud(
        self,
        project_id: int,
        remote_folder: Optional[str] = None,
    ) -> Dict:
        """
        Import files from Nextcloud into a project (bidirectional sync)

        Args:
            project_id: Project to import into
            remote_folder: Remote folder to import from (uses project folder if None)

        Returns:
            Import summary
        """
        # Load project
        result = await self.db.execute(
            select(Project).where(Project.id == project_id)
        )
        project = result.scalar_one_or_none()

        if not project:
            raise ValueError(f"Project {project_id} not found")

        # Determine remote folder
        if remote_folder is None:
            folders = self._get_project_folder_structure(project)
            remote_folder = folders["originals"]

        # List files in Nextcloud
        try:
            logger.info(f"Listing files in Nextcloud: {remote_folder}")
            files = await self.nextcloud_client.list_files(
                directory=remote_folder,
                recursive=False,
            )

            # Filter for supported file types
            image_files = [
                f
                for f in files
                if not f["is_dir"]
                and Path(f["name"]).suffix.lower().lstrip(".")
                in (settings.allowed_image_exts + settings.allowed_video_exts)
            ]

            return {
                "success": True,
                "project_id": project_id,
                "project_name": project.name,
                "remote_folder": remote_folder,
                "total_files": len(files),
                "importable_files": len(image_files),
                "files": [
                    {
                        "name": f["name"],
                        "size": f["size"],
                        "path": f["path"],
                    }
                    for f in image_files
                ],
                "message": "Import not yet implemented - this would download and create database records",
            }

        except Exception as e:
            logger.error(f"Error importing from Nextcloud: {e}")
            return {
                "success": False,
                "error": str(e),
            }

    async def get_sync_status(self, project_id: int) -> Dict:
        """
        Get sync status for a project

        Args:
            project_id: Project ID

        Returns:
            Sync status information
        """
        # Load project with images
        result = await self.db.execute(
            select(Project)
            .options(selectinload(Project.images))
            .where(Project.id == project_id)
        )
        project = result.scalar_one_or_none()

        if not project:
            raise ValueError(f"Project {project_id} not found")

        total_images = len(project.images)
        synced_to_nextcloud = sum(
            1
            for img in project.images
            if img.storage_type == StorageType.NEXTCLOUD and img.nextcloud_path
        )
        local_only = total_images - synced_to_nextcloud

        return {
            "project_id": project.id,
            "project_name": project.name,
            "nextcloud_folder": project.nextcloud_folder,
            "total_assets": total_images,
            "synced_to_nextcloud": synced_to_nextcloud,
            "local_only": local_only,
            "sync_percentage": (
                (synced_to_nextcloud / total_images * 100) if total_images > 0 else 0
            ),
            "auto_sync_enabled": self.auto_sync,
        }

    async def validate_nextcloud_connection(self) -> Dict:
        """
        Test Nextcloud connection and validate configuration

        Returns:
            Connection status
        """
        try:
            # Try to list root directory
            files = await self.nextcloud_client.list_files(directory="")

            return {
                "success": True,
                "message": "Connected to Nextcloud successfully",
                "url": self.nextcloud_client.url,
                "username": self.nextcloud_client.username,
                "base_path": self.nextcloud_client.base_path,
                "files_in_root": len(files),
            }

        except Exception as e:
            logger.error(f"Nextcloud connection validation failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "url": self.nextcloud_client.url,
                "username": self.nextcloud_client.username,
            }
