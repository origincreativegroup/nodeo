"""Project management service for portfolio organization"""
from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional, Sequence, TYPE_CHECKING

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import (
    GroupType,
    Image,
    ImageGroup,
    ImageGroupAssociation,
    Project,
    ProjectType,
)
from app.storage.layout import _slugify_segment

if TYPE_CHECKING:
    from app.storage.nextcloud_sync import NextcloudSyncService


class ProjectService:
    """Service for managing portfolio projects and asset assignments"""

    def __init__(
        self,
        db: AsyncSession,
        sync_service: Optional["NextcloudSyncService"] = None,
    ):
        self.db = db
        self.sync_service = sync_service

    async def create_project(
        self,
        name: str,
        project_type: ProjectType = ProjectType.PERSONAL,
        description: Optional[str] = None,
        ai_keywords: Optional[List[str]] = None,
        visual_themes: Optional[Dict] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        nextcloud_folder: Optional[str] = None,
        default_naming_template: Optional[str] = None,
        portfolio_metadata: Optional[Dict] = None,
        featured_on_portfolio: bool = False,
    ) -> Project:
        """
        Create a new portfolio project

        Args:
            name: Project name (must be unique)
            project_type: Type of project (client, personal, etc.)
            description: Project description
            ai_keywords: Keywords for AI project matching
            visual_themes: Color palettes, styles, visual patterns
            start_date: Project start date
            end_date: Project end date
            nextcloud_folder: Dedicated Nextcloud folder path
            default_naming_template: Project-specific naming template
            portfolio_metadata: Client, industry, URL, testimonials, etc.
            featured_on_portfolio: Whether to feature on portfolio

        Returns:
            Created project
        """
        # Generate slug from name
        slug = _slugify_segment(name)

        # Check if slug already exists
        result = await self.db.execute(
            select(Project).where(Project.slug == slug)
        )
        existing = result.scalar_one_or_none()
        if existing:
            raise ValueError(f"Project with slug '{slug}' already exists")

        # Auto-generate Nextcloud folder if not provided
        if nextcloud_folder is None:
            nextcloud_folder = f"projects/{slug}"

        project = Project(
            name=name,
            slug=slug,
            project_type=project_type,
            description=description,
            ai_keywords=ai_keywords or [],
            visual_themes=visual_themes or {},
            start_date=start_date,
            end_date=end_date,
            nextcloud_folder=nextcloud_folder,
            default_naming_template=default_naming_template,
            portfolio_metadata=portfolio_metadata or {},
            featured_on_portfolio=featured_on_portfolio,
        )

        self.db.add(project)
        await self.db.commit()
        await self.db.refresh(project)
        return project

    async def get_project(self, project_id: int) -> Optional[Project]:
        """Get project by ID with relationships loaded"""
        result = await self.db.execute(
            select(Project)
            .options(selectinload(Project.images), selectinload(Project.groups))
            .where(Project.id == project_id)
        )
        return result.scalar_one_or_none()

    async def get_project_by_slug(self, slug: str) -> Optional[Project]:
        """Get project by slug"""
        result = await self.db.execute(
            select(Project)
            .options(selectinload(Project.images), selectinload(Project.groups))
            .where(Project.slug == slug)
        )
        return result.scalar_one_or_none()

    async def list_projects(
        self,
        project_type: Optional[ProjectType] = None,
        is_active: Optional[bool] = None,
        featured_only: bool = False,
    ) -> List[Project]:
        """
        List all projects with optional filtering

        Args:
            project_type: Filter by project type
            is_active: Filter by active status
            featured_only: Only return featured projects

        Returns:
            List of projects
        """
        query = select(Project).options(
            selectinload(Project.images), selectinload(Project.groups)
        )

        if project_type:
            query = query.where(Project.project_type == project_type)

        if is_active is not None:
            query = query.where(Project.is_active == is_active)

        if featured_only:
            query = query.where(Project.featured_on_portfolio == True)

        query = query.order_by(Project.created_at.desc())

        result = await self.db.execute(query)
        return list(result.scalars().unique().all())

    async def update_project(
        self,
        project_id: int,
        **updates,
    ) -> Project:
        """
        Update project fields

        Args:
            project_id: Project ID
            **updates: Fields to update

        Returns:
            Updated project
        """
        project = await self.get_project(project_id)
        if not project:
            raise ValueError(f"Project {project_id} not found")

        # Update fields
        for key, value in updates.items():
            if hasattr(project, key):
                setattr(project, key, value)

        await self.db.commit()
        await self.db.refresh(project)
        return project

    async def delete_project(self, project_id: int) -> bool:
        """
        Delete (archive) a project

        Args:
            project_id: Project ID

        Returns:
            True if successful
        """
        project = await self.get_project(project_id)
        if not project:
            return False

        # Set as inactive instead of deleting
        project.is_active = False
        await self.db.commit()
        return True

    async def assign_images_to_project(
        self,
        project_id: int,
        image_ids: Sequence[int],
        replace: bool = False,
    ) -> Project:
        """
        Assign images to a project

        Args:
            project_id: Project ID
            image_ids: List of image IDs to assign
            replace: If True, remove existing assignments first

        Returns:
            Updated project
        """
        project = await self.get_project(project_id)
        if not project:
            raise ValueError(f"Project {project_id} not found")

        if replace:
            # Remove all existing assignments
            result = await self.db.execute(
                select(Image).where(Image.project_id == project_id)
            )
            for image in result.scalars():
                image.project_id = None

        # Assign new images
        newly_assigned_ids = []
        for image_id in image_ids:
            result = await self.db.execute(
                select(Image).where(Image.id == image_id)
            )
            image = result.scalar_one_or_none()
            if image:
                image.project_id = project_id
                newly_assigned_ids.append(image_id)

        await self.db.commit()
        await self.db.refresh(project)

        # Trigger Nextcloud sync if available
        if self.sync_service and newly_assigned_ids:
            for image_id in newly_assigned_ids:
                try:
                    await self.sync_service.sync_image_on_assignment(
                        image_id=image_id,
                        project_id=project_id,
                    )
                except Exception as e:
                    # Log but don't fail the assignment
                    import logging
                    logging.warning(f"Failed to sync image {image_id} to Nextcloud: {e}")

        return project

    async def remove_images_from_project(
        self,
        project_id: int,
        image_ids: Sequence[int],
    ) -> Project:
        """
        Remove images from a project

        Args:
            project_id: Project ID
            image_ids: List of image IDs to remove

        Returns:
            Updated project
        """
        project = await self.get_project(project_id)
        if not project:
            raise ValueError(f"Project {project_id} not found")

        # Remove assignments
        for image_id in image_ids:
            result = await self.db.execute(
                select(Image).where(
                    Image.id == image_id, Image.project_id == project_id
                )
            )
            image = result.scalar_one_or_none()
            if image:
                image.project_id = None

        await self.db.commit()
        await self.db.refresh(project)
        return project

    async def get_unassigned_images(self) -> List[Image]:
        """Get all images not assigned to any project"""
        result = await self.db.execute(
            select(Image).where(Image.project_id.is_(None))
        )
        return list(result.scalars().all())

    async def get_project_stats(self, project_id: int) -> Dict:
        """
        Get statistics for a project

        Args:
            project_id: Project ID

        Returns:
            Dictionary with project statistics
        """
        project = await self.get_project(project_id)
        if not project:
            raise ValueError(f"Project {project_id} not found")

        # Count images
        result = await self.db.execute(
            select(Image).where(Image.project_id == project_id)
        )
        images = list(result.scalars().all())

        # Calculate stats
        total_images = len(images)
        analyzed_images = sum(1 for img in images if img.analyzed_at)
        total_size = sum(img.file_size for img in images)

        # Count by media type
        image_count = sum(1 for img in images if img.media_type.value == "image")
        video_count = sum(1 for img in images if img.media_type.value == "video")

        # Count by storage type
        storage_counts = {}
        for img in images:
            storage_type = img.storage_type.value
            storage_counts[storage_type] = storage_counts.get(storage_type, 0) + 1

        return {
            "project_id": project_id,
            "project_name": project.name,
            "total_assets": total_images,
            "analyzed_assets": analyzed_images,
            "image_count": image_count,
            "video_count": video_count,
            "total_size_bytes": total_size,
            "storage_distribution": storage_counts,
            "start_date": project.start_date.isoformat() if project.start_date else None,
            "end_date": project.end_date.isoformat() if project.end_date else None,
        }

    async def create_project_group(self, project_id: int) -> ImageGroup:
        """
        Create or update a project-based image group

        Args:
            project_id: Project ID

        Returns:
            Created or updated image group
        """
        project = await self.get_project(project_id)
        if not project:
            raise ValueError(f"Project {project_id} not found")

        # Check if group already exists
        result = await self.db.execute(
            select(ImageGroup)
            .options(selectinload(ImageGroup.assignments))
            .where(
                ImageGroup.group_type == GroupType.AI_PROJECT_CLUSTER,
                ImageGroup.project_id == project_id,
            )
        )
        group = result.scalar_one_or_none()

        if not group:
            # Create new group
            group = ImageGroup(
                name=f"Project: {project.name}",
                description=project.description,
                group_type=GroupType.AI_PROJECT_CLUSTER,
                project_id=project_id,
                attributes={
                    "project_slug": project.slug,
                    "project_type": project.project_type.value,
                },
            )
            self.db.add(group)
            await self.db.flush()

        # Get all images for this project
        result = await self.db.execute(
            select(Image).where(Image.project_id == project_id)
        )
        project_images = list(result.scalars().all())

        # Update group membership
        existing_ids = {assignment.image_id for assignment in group.assignments}
        target_ids = {img.id for img in project_images}

        # Add new assignments
        for image_id in target_ids - existing_ids:
            self.db.add(
                ImageGroupAssociation(group_id=group.id, image_id=image_id)
            )

        # Remove old assignments
        for assignment in list(group.assignments):
            if assignment.image_id not in target_ids:
                await self.db.delete(assignment)

        # Update metadata
        group.attributes = {
            **(group.attributes or {}),
            "project_slug": project.slug,
            "project_type": project.project_type.value,
            "image_count": len(target_ids),
        }

        await self.db.commit()
        await self.db.refresh(group)
        return group
