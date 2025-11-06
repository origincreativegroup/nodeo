"""Project-aware rename service for portfolio assets"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Image, Project
from app.services.rename_engine import RenameEngine
from app.services.template_parser import TemplateParser

logger = logging.getLogger(__name__)


@dataclass
class ProjectRenamePreview:
    """Preview of a project-aware rename operation"""

    image_id: int
    original_filename: str
    proposed_filename: str
    project_name: str
    project_number: int
    metadata: Dict


class ProjectRenameService:
    """Service for project-aware asset renaming"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_next_project_number(self, project_id: int) -> int:
        """
        Get the next sequential number for assets in a project

        Args:
            project_id: Project ID

        Returns:
            Next sequential number (1-indexed)
        """
        # Count existing images in project
        result = await self.db.execute(
            select(func.count(Image.id)).where(Image.project_id == project_id)
        )
        count = result.scalar() or 0
        return count + 1

    async def prepare_metadata_with_project(
        self,
        image: Image,
        project: Optional[Project] = None,
        project_number: Optional[int] = None,
    ) -> Dict:
        """
        Prepare metadata dict with project information for template rendering

        Args:
            image: Image to prepare metadata for
            project: Project (loaded if not provided)
            project_number: Sequential number (calculated if not provided)

        Returns:
            Metadata dict with all template variables
        """
        # Load project if not provided
        if not project and image.project_id:
            result = await self.db.execute(
                select(Project).where(Project.id == image.project_id)
            )
            project = result.scalar_one_or_none()

        # Calculate project number if not provided
        if project_number is None and project:
            project_number = await self.get_next_project_number(project.id)

        # Extract client from portfolio metadata
        client = ""
        if project and project.portfolio_metadata:
            client = project.portfolio_metadata.get("client", "")

        # Prepare metadata
        metadata = {
            # Basic AI metadata
            "description": image.ai_description or "",
            "tags": image.ai_tags or [],
            "scene": image.ai_scene or "",
            "objects": image.ai_objects or [],

            # File metadata
            "original_filename": image.original_filename,
            "width": image.width,
            "height": image.height,
            "duration_s": image.duration_s,
            "frame_rate": image.frame_rate,
            "codec": image.codec,
            "format": image.media_format,
            "media_type": image.media_type.value if image.media_type else "",

            # Project metadata
            "project": project.slug if project else "",
            "project_name": project.name if project else "",
            "client": client,
            "project_type": project.project_type.value if project else "",
            "project_number": project_number or 1,
        }

        return metadata

    async def preview_project_rename(
        self,
        project_id: int,
        template: str,
    ) -> List[ProjectRenamePreview]:
        """
        Preview renaming all assets in a project

        Args:
            project_id: Project ID
            template: Naming template to use

        Returns:
            List of rename previews
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

        # Sort images by creation date for consistent numbering
        images = sorted(project.images, key=lambda img: img.created_at)

        # Create parser
        parser = TemplateParser(template)

        # Generate previews
        previews = []
        for idx, image in enumerate(images, start=1):
            # Prepare metadata with project info
            metadata = await self.prepare_metadata_with_project(
                image=image,
                project=project,
                project_number=idx,
            )

            # Generate proposed filename
            ext = Path(image.current_filename).suffix
            proposed_base = parser.apply(metadata, index=idx)
            proposed_filename = f"{proposed_base}{ext}"

            previews.append(
                ProjectRenamePreview(
                    image_id=image.id,
                    original_filename=image.current_filename,
                    proposed_filename=proposed_filename,
                    project_name=project.name,
                    project_number=idx,
                    metadata=metadata,
                )
            )

        return previews

    async def apply_project_rename(
        self,
        project_id: int,
        template: str,
        create_backups: bool = True,
    ) -> Dict:
        """
        Apply project-aware rename to all assets in a project

        Args:
            project_id: Project ID
            template: Naming template to use
            create_backups: Create backup files before renaming

        Returns:
            Summary of rename operation
        """
        # Get previews
        previews = await self.preview_project_rename(project_id, template)

        # Create rename engine
        engine = RenameEngine(template)

        # Build rename specs
        rename_specs = []
        for preview in previews:
            result = await self.db.execute(
                select(Image).where(Image.id == preview.image_id)
            )
            image = result.scalar_one_or_none()
            if image:
                rename_specs.append(
                    {
                        "file_path": image.file_path,
                        "new_filename": preview.proposed_filename,
                    }
                )

        # Apply renames
        result = engine.apply_batch_rename(
            rename_specs=rename_specs,
            create_backups=create_backups,
            stop_on_error=False,
        )

        # Update database for successful renames
        for i, rename_result in enumerate(result["results"]):
            if rename_result["success"] and i < len(previews):
                preview = previews[i]
                image_result = await self.db.execute(
                    select(Image).where(Image.id == preview.image_id)
                )
                image = image_result.scalar_one_or_none()
                if image:
                    image.current_filename = preview.proposed_filename
                    image.file_path = rename_result["new_path"]

        await self.db.commit()

        return {
            "success": True,
            "project_id": project_id,
            "total": result["total"],
            "succeeded": result["succeeded"],
            "failed": result["failed"],
            "results": result["results"],
        }

    async def rename_single_with_project(
        self,
        image_id: int,
        template: Optional[str] = None,
        create_backup: bool = True,
    ) -> Dict:
        """
        Rename a single image using project context

        Args:
            image_id: Image ID
            template: Template to use (uses project default if None)
            create_backup: Create backup before renaming

        Returns:
            Rename result
        """
        # Load image with project
        result = await self.db.execute(
            select(Image)
            .options(selectinload(Image.project))
            .where(Image.id == image_id)
        )
        image = result.scalar_one_or_none()

        if not image:
            raise ValueError(f"Image {image_id} not found")

        # Use project default template if available
        if template is None and image.project:
            template = image.project.default_naming_template

        # Fall back to simple template
        if template is None:
            template = "{project}_{description}_{project_number}"

        # Get project number
        project_number = 1
        if image.project:
            project_number = await self.get_next_project_number(image.project.id)

        # Prepare metadata
        metadata = await self.prepare_metadata_with_project(
            image=image,
            project=image.project,
            project_number=project_number,
        )

        # Generate filename
        parser = TemplateParser(template)
        ext = Path(image.current_filename).suffix
        proposed_base = parser.apply(metadata)
        proposed_filename = f"{proposed_base}{ext}"

        # Apply rename
        engine = RenameEngine(template)
        rename_result = engine.apply_rename(
            file_path=image.file_path,
            new_filename=proposed_filename,
            create_backup=create_backup,
        )

        # Update database if successful
        if rename_result["success"]:
            image.current_filename = proposed_filename
            image.file_path = rename_result["new_path"]
            await self.db.commit()

        return {
            "success": rename_result["success"],
            "image_id": image_id,
            "original_filename": image.original_filename,
            "new_filename": proposed_filename if rename_result["success"] else None,
            "project_name": image.project.name if image.project else None,
            "project_number": project_number,
            "error": rename_result.get("error"),
        }

    async def get_portfolio_suggestions(self, project_id: int) -> Dict:
        """
        Get template suggestions for a portfolio project

        Args:
            project_id: Project ID

        Returns:
            Dict with template suggestions and examples
        """
        # Load project
        result = await self.db.execute(
            select(Project).where(Project.id == project_id)
        )
        project = result.scalar_one_or_none()

        if not project:
            raise ValueError(f"Project {project_id} not found")

        # Get sample image for previews
        sample_result = await self.db.execute(
            select(Image)
            .where(Image.project_id == project_id)
            .limit(1)
        )
        sample_image = sample_result.scalar_one_or_none()

        if not sample_image:
            return {
                "project_name": project.name,
                "suggestions": [],
                "message": "No images in project yet",
            }

        # Prepare sample metadata
        sample_metadata = await self.prepare_metadata_with_project(
            image=sample_image,
            project=project,
            project_number=1,
        )

        # Generate previews for portfolio templates
        from app.services.template_parser import PREDEFINED_TEMPLATES

        suggestions = []
        for name, template in PREDEFINED_TEMPLATES.items():
            if name.startswith("portfolio_"):
                parser = TemplateParser(template)
                ext = Path(sample_image.current_filename).suffix
                preview = parser.apply(sample_metadata)
                suggestions.append(
                    {
                        "name": name,
                        "template": template,
                        "example": f"{preview}{ext}",
                        "description": self._get_template_description(name),
                    }
                )

        return {
            "project_id": project_id,
            "project_name": project.name,
            "client": sample_metadata.get("client", ""),
            "suggestions": suggestions,
        }

    def _get_template_description(self, template_name: str) -> str:
        """Get human-readable description for template"""
        descriptions = {
            "portfolio_client": "Professional format with client name",
            "portfolio_seo": "SEO-friendly with full project name",
            "portfolio_numbered": "Simple sequential numbering",
            "portfolio_dated": "Dated with project context",
            "portfolio_detailed": "Detailed with client and project type",
            "portfolio_simple": "Clean and minimal",
            "portfolio_professional": "Professional with tags",
            "portfolio_web": "Optimized for web publishing",
        }
        return descriptions.get(template_name, "Custom template")
