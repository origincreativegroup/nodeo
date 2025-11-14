"""
File processor worker for JSPOW v2

Handles file import, AI analysis, and suggestion generation
"""
import logging
import shutil
from pathlib import Path
from typing import Optional
from uuid import UUID, uuid4
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal
from app.models import (
    WatchedFolder,
    Image,
    MediaType,
    StorageType,
    RenameSuggestion,
    SuggestionStatus,
    ActivityLog,
    ActivityActionType,
    Tag,
    TagType,
    AssetTag,
)
from app.config import settings
from app.ai import llava_client
from app.services import MediaMetadataService, RenameEngine
from app.storage import storage_manager

logger = logging.getLogger(__name__)


class FileProcessor:
    """Processes files detected by folder watcher"""

    def __init__(self):
        self.default_template = "{description}_{date}"  # Default rename template

    async def process_file(
        self,
        folder_id: UUID,
        file_path: str
    ) -> bool:
        """
        Process a single file from watched folder

        Steps:
        1. Check if file already exists in database
        2. Import file into storage
        3. Create Image record
        4. Analyze with AI
        5. Generate rename suggestion
        6. Update folder stats
        7. Create activity log

        Returns:
            bool: True if processing succeeded, False otherwise
        """
        async with AsyncSessionLocal() as db:
            try:
                # Get watched folder
                result = await db.execute(
                    select(WatchedFolder).where(WatchedFolder.id == folder_id)
                )
                folder = result.scalar_one_or_none()

                if not folder:
                    logger.error(f"Watched folder {folder_id} not found")
                    return False

                # Check if file exists and is readable
                path = Path(file_path)
                if not path.exists():
                    logger.warning(f"File no longer exists: {file_path}")
                    return False

                # Check if already imported
                existing = await db.execute(
                    select(Image).where(Image.file_path == str(path))
                )
                if existing.scalar_one_or_none():
                    logger.info(f"File already imported: {file_path}")
                    return True

                # Determine media type
                ext = path.suffix.lower().lstrip('.')
                is_image = ext in settings.allowed_image_exts
                is_video = ext in settings.allowed_video_exts

                if not (is_image or is_video):
                    logger.warning(f"Unsupported file type: {ext}")
                    return False

                media_type = MediaType.IMAGE if is_image else MediaType.VIDEO

                # Read file
                with open(path, 'rb') as f:
                    content = f.read()

                # Import into storage
                asset_id = uuid4().hex
                uploaded_at = datetime.utcnow()
                project_code = settings.default_project_code

                # Write to originals (copy, don't move - preserve source)
                original_path = storage_manager.write_file(
                    "originals",
                    asset_id,
                    path.name,
                    content,
                    created_at=uploaded_at,
                    project=project_code,
                )

                # Write to working directory
                working_path = storage_manager.write_file(
                    "working",
                    asset_id,
                    path.name,
                    content,
                    created_at=uploaded_at,
                    project=project_code,
                )

                # Write metadata
                storage_manager.write_metadata(
                    asset_id,
                    {
                        "asset_id": asset_id,
                        "project": project_code,
                        "project_slug": storage_manager.project_slug(project_code),
                        "original_path": str(original_path),
                        "working_path": str(working_path),
                        "source_path": str(path),
                        "uploaded_at": uploaded_at.isoformat(),
                        "watched_folder_id": str(folder_id),
                        "published": False,
                    },
                    created_at=uploaded_at,
                    project=project_code,
                )

                # Get media metadata
                metadata_service = MediaMetadataService(db)
                metadata_result = await metadata_service.get_metadata(
                    working_path,
                    mime_type=f"{'image' if is_image else 'video'}/{ext}"
                )

                # Create Image record
                image = Image(
                    original_filename=path.name,
                    current_filename=path.name,
                    file_path=str(working_path),
                    file_size=len(content),
                    mime_type=f"{'image' if is_image else 'video'}/{ext}",
                    media_type=media_type,
                    width=metadata_result.width,
                    height=metadata_result.height,
                    duration_s=metadata_result.duration_s,
                    frame_rate=metadata_result.frame_rate,
                    codec=metadata_result.codec,
                    media_format=metadata_result.format,
                    metadata_id=metadata_result.metadata_id,
                    storage_type=StorageType.LOCAL,
                )

                db.add(image)
                await db.flush()
                await db.refresh(image)

                logger.info(f"Imported file {path.name} as asset {image.id}")

                # Analyze with AI (only for images for now)
                if is_image:
                    try:
                        ai_metadata = await llava_client.extract_metadata(str(working_path))

                        image.ai_description = ai_metadata.get('description')
                        image.ai_tags = ai_metadata.get('tags', [])
                        image.ai_objects = ai_metadata.get('objects', [])
                        image.ai_scene = ai_metadata.get('scene')
                        image.analyzed_at = datetime.utcnow()

                        await db.flush()

                        logger.info(f"AI analysis completed for {path.name}")

                        # Create/update tags
                        await self._process_tags(db, image, ai_metadata.get('tags', []))

                    except Exception as e:
                        logger.error(f"Error analyzing {path.name} with AI: {e}")
                        # Continue processing even if AI fails

                # Generate rename suggestion
                suggestion = await self._generate_suggestion(
                    db,
                    folder_id,
                    image,
                    str(path)
                )

                # Update folder stats
                folder.analyzed_count += 1
                if suggestion:
                    folder.pending_count += 1

                await db.commit()

                # Create activity log
                activity_log = ActivityLog(
                    watched_folder_id=folder_id,
                    asset_id=image.id,
                    action_type=ActivityActionType.SCAN,
                    original_filename=path.name,
                    folder_path=str(path.parent),
                    status="success",
                    metadata={
                        "asset_id": image.id,
                        "analyzed": image.analyzed_at is not None,
                        "suggestion_created": suggestion is not None
                    }
                )
                db.add(activity_log)
                await db.commit()

                logger.info(f"Successfully processed {path.name}")
                return True

            except Exception as e:
                logger.error(f"Error processing file {file_path}: {e}", exc_info=True)

                # Create error activity log
                try:
                    error_log = ActivityLog(
                        watched_folder_id=folder_id,
                        action_type=ActivityActionType.ERROR,
                        original_filename=Path(file_path).name,
                        folder_path=str(Path(file_path).parent),
                        status="failure",
                        error_message=str(e)
                    )
                    db.add(error_log)
                    await db.commit()
                except:
                    pass

                return False

    async def _generate_suggestion(
        self,
        db: AsyncSession,
        folder_id: UUID,
        image: Image,
        original_path: str
    ) -> Optional[RenameSuggestion]:
        """
        Generate rename suggestion for an image

        Returns:
            RenameSuggestion if generated successfully, None otherwise
        """
        try:
            if not image.ai_description:
                logger.warning(f"No AI description for image {image.id}, skipping suggestion")
                return None

            # Use RenameEngine to generate filename
            engine = RenameEngine(template=self.default_template)

            metadata = {
                'description': image.ai_description or '',
                'tags': image.ai_tags or [],
                'scene': image.ai_scene or '',
                'original_filename': image.original_filename,
                'width': image.width,
                'height': image.height,
                'duration_s': image.duration_s,
                'frame_rate': image.frame_rate,
                'codec': image.codec,
                'format': image.media_format,
                'media_type': image.media_type.value if image.media_type else None,
            }

            ext = Path(image.current_filename).suffix
            suggested_name = engine.generate_filename(metadata, index=1, original_extension=ext)

            # Calculate confidence score based on AI metadata quality
            confidence = self._calculate_confidence(image)

            # Only create suggestion if confidence meets threshold
            if confidence < settings.suggestion_confidence_threshold:
                logger.info(
                    f"Confidence {confidence:.2f} below threshold "
                    f"{settings.suggestion_confidence_threshold}, skipping suggestion"
                )
                return None

            # Create suggestion
            suggestion = RenameSuggestion(
                watched_folder_id=folder_id,
                asset_id=image.id,
                original_path=original_path,
                original_filename=image.original_filename,
                suggested_filename=suggested_name,
                description=image.ai_description,
                confidence_score=confidence,
                status=SuggestionStatus.PENDING
            )

            db.add(suggestion)
            await db.flush()

            logger.info(
                f"Created rename suggestion for {image.original_filename} -> "
                f"{suggested_name} (confidence: {confidence:.2f})"
            )

            return suggestion

        except Exception as e:
            logger.error(f"Error generating suggestion for image {image.id}: {e}")
            return None

    def _calculate_confidence(self, image: Image) -> float:
        """
        Calculate confidence score for rename suggestion

        Factors:
        - Has description (0.5)
        - Has tags (0.3)
        - Has scene (0.2)
        - Description length (bonus up to 0.1)
        - Tag count (bonus up to 0.1)
        """
        confidence = 0.0

        # Base score for having description
        if image.ai_description:
            confidence += 0.5
            # Bonus for detailed description
            desc_len = len(image.ai_description)
            if desc_len > 50:
                confidence += min(0.1, desc_len / 1000)

        # Score for having tags
        if image.ai_tags and len(image.ai_tags) > 0:
            confidence += 0.3
            # Bonus for multiple tags
            tag_count = len(image.ai_tags)
            if tag_count > 3:
                confidence += min(0.1, tag_count / 50)

        # Score for having scene
        if image.ai_scene:
            confidence += 0.2

        return min(1.0, confidence)

    async def _process_tags(
        self,
        db: AsyncSession,
        image: Image,
        tag_names: list
    ):
        """
        Process AI-detected tags and create Tag/AssetTag relationships
        """
        if not tag_names:
            return

        for tag_name in tag_names:
            if not tag_name or not isinstance(tag_name, str):
                continue

            tag_name = tag_name.strip().lower()
            if not tag_name:
                continue

            # Get or create tag
            result = await db.execute(
                select(Tag).where(Tag.name == tag_name)
            )
            tag = result.scalar_one_or_none()

            if not tag:
                tag = Tag(
                    name=tag_name,
                    tag_type=TagType.AI,
                    usage_count=0
                )
                db.add(tag)
                await db.flush()

            # Create asset-tag relationship
            asset_tag = AssetTag(
                asset_id=image.id,
                tag_id=tag.id,
                confidence=0.8  # Default AI confidence
            )
            db.add(asset_tag)

            # Increment usage count
            tag.usage_count += 1

        await db.flush()


# Global file processor instance
file_processor = FileProcessor()
