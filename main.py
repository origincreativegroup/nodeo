"""jspow - AI-powered image file renaming and organization tool
Main FastAPI application"""
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional

from fastapi import BackgroundTasks, Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from pydantic import BaseModel, Field
import logging
import uvicorn
from datetime import datetime
from uuid import uuid4

from app.config import settings
from app.database import init_db, close_db, get_db
from app.models import (
    GroupType,
    Image,
    ImageGroup,
    ImageGroupAssociation,
    MediaType,
    ProcessStatus,
    ProcessingQueue,
    RenameJob,
    StorageType,
    Template,
    UploadBatch,
)
from app.ai import llava_client
from app.services import (
    GroupingService,
    GroupSummary,
    MediaMetadataService,
    RenameEngine,
    TemplateParser,
    PREDEFINED_TEMPLATES,
)
from app.storage import nextcloud_client, r2_client, stream_client, storage_manager

# Configure logging
logging.basicConfig(
    level=logging.INFO if settings.debug else logging.WARNING,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def serialize_group(group: ImageGroup) -> Dict[str, Any]:
    """Serialize an ImageGroup instance into a JSON-friendly dict."""

    return {
        "id": group.id,
        "name": group.name,
        "description": group.description,
        "group_type": group.group_type.value if group.group_type else None,
        "metadata": group.attributes or {},
        "is_user_defined": group.is_user_defined,
        "created_by": group.created_by,
        "image_ids": [assignment.image_id for assignment in group.assignments],
        "created_at": group.created_at.isoformat() if group.created_at else None,
        "upload_batch_id": group.upload_batch_id,
    }


def serialize_group_summary(summary: GroupSummary) -> Dict[str, Any]:
    """Serialize a GroupSummary instance returned by the grouping service."""

    return {
        "id": summary.id,
        "name": summary.name,
        "group_type": summary.group_type,
        "description": summary.description,
        "metadata": summary.metadata,
        "image_ids": summary.image_ids,
        "is_user_defined": summary.is_user_defined,
        "created_by": summary.created_by,
        "created_at": summary.created_at,
    }


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup/shutdown"""
    # Startup
    logger.info("Starting jspow application...")
    await init_db()
    logger.info("Database initialized")

    # Create storage directories
    storage_manager.ensure_layout()
    Path(settings.upload_dir).mkdir(parents=True, exist_ok=True)
    logger.info(f"Storage root: {storage_manager.root}")
    logger.info(f"Working directory: {settings.upload_dir}")

    yield

    # Shutdown
    logger.info("Shutting down jspow...")
    await close_db()
    logger.info("Shutdown complete")


# Create FastAPI app
app = FastAPI(
    title="jspow",
    description="AI-powered image file renaming and organization tool",
    version=settings.app_version,
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "app": settings.app_name,
        "version": settings.app_version
    }


# Image upload and analysis endpoints
@app.post("/api/images/upload")
async def upload_images(
    files: List[UploadFile] = File(...),
    db: AsyncSession = Depends(get_db),
    background_tasks: BackgroundTasks = None
):
    """
    Upload and analyze images
    """
    if len(files) > settings.max_batch_size:
        raise HTTPException(
            status_code=400,
            detail=f"Maximum {settings.max_batch_size} files allowed"
        )

    results = []
    metadata_service = MediaMetadataService(db)

    upload_label = datetime.utcnow().strftime("Upload %Y-%m-%d %H:%M")
    upload_batch = UploadBatch(
        label=upload_label,
        source="web",
        attributes={"total_expected": len(files)},
    )
    db.add(upload_batch)
    await db.flush()

    upload_group = ImageGroup(
        name=upload_label,
        group_type=GroupType.UPLOAD_BATCH,
        attributes={
            "cluster_key": f"upload:{upload_batch.id}",
            "total_expected": len(files),
            "image_count": 0,
        },
        upload_batch_id=upload_batch.id,
    )
    db.add(upload_group)
    await db.flush()
    await db.commit()

    successful_image_ids: List[int] = []

    for file in files:
        try:
            # Validate file extension
            ext = Path(file.filename).suffix.lower().lstrip('.')
            is_image = ext in settings.allowed_image_exts
            is_video = ext in settings.allowed_video_exts
            if not (is_image or is_video):
                results.append({
                    "filename": file.filename,
                    "success": False,
                    "error": f"Invalid file type: {ext}"
                })
                continue

            # Save file into storage layout
            content = await file.read()
            uploaded_at = datetime.utcnow()
            asset_id = uuid4().hex
            project_code = settings.default_project_code

            original_path = storage_manager.write_file(
                "originals",
                asset_id,
                file.filename,
                content,
                created_at=uploaded_at,
                project=project_code,
            )
            working_path = storage_manager.write_file(
                "working",
                asset_id,
                file.filename,
                content,
                created_at=uploaded_at,
                project=project_code,
            )

            storage_manager.write_metadata(
                asset_id,
                {
                    "asset_id": asset_id,
                    "project": project_code,
                    "project_slug": storage_manager.project_slug(project_code),
                    "original_path": str(original_path),
                    "working_path": str(working_path),
                    "uploaded_at": uploaded_at.isoformat(),
                    "published": False,
                },
                created_at=uploaded_at,
                project=project_code,
            )

            # Create database record
            metadata_result = await metadata_service.get_metadata(working_path, mime_type=file.content_type)
            media_type = MediaType(metadata_result.media_type) if metadata_result.media_type else (MediaType.IMAGE if is_image else MediaType.VIDEO)
            image_record = Image(
                original_filename=file.filename,
                current_filename=file.filename,
                file_path=str(working_path),
                file_size=len(content),
                mime_type=file.content_type,
                media_type=media_type,
                width=metadata_result.width,
                height=metadata_result.height,
                duration_s=metadata_result.duration_s,
                frame_rate=metadata_result.frame_rate,
                codec=metadata_result.codec,
                media_format=metadata_result.format,
                metadata_id=metadata_result.metadata_id,
                storage_type=StorageType.LOCAL,
                upload_batch_id=upload_batch.id,
            )

            db.add(image_record)
            await db.flush()

            db.add(
                ImageGroupAssociation(
                    group_id=upload_group.id,
                    image_id=image_record.id,
                )
            )

            await db.commit()
            await db.refresh(image_record)

            results.append({
                "filename": file.filename,
                "success": True,
                "id": image_record.id,
                "size": len(content),
                "dimensions": f"{metadata_result.width}x{metadata_result.height}" if metadata_result.width and metadata_result.height else None,
                "metadata": metadata_result.to_dict(),
            })
            successful_image_ids.append(image_record.id)

        except Exception as e:
            logger.error(f"Error uploading {file.filename}: {e}")
            results.append({
                "filename": file.filename,
                "success": False,
                "error": str(e)
            })

    upload_group.attributes = {
        **(upload_group.attributes or {}),
        "image_count": len(successful_image_ids),
    }
    await db.commit()

    return {
        "total": len(files),
        "succeeded": sum(1 for r in results if r.get("success")),
        "results": results,
        "upload_batch_id": upload_batch.id,
        "group_id": upload_group.id,
    }


@app.post("/api/images/{image_id}/analyze")
async def analyze_image(
    image_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Analyze image with LLaVA AI
    """
    from sqlalchemy import select
    from datetime import datetime

    # Get image record
    result = await db.execute(select(Image).where(Image.id == image_id))
    image = result.scalar_one_or_none()

    if not image:
        raise HTTPException(status_code=404, detail="Image not found")

    try:
        # Analyze with LLaVA
        metadata = await llava_client.extract_metadata(image.file_path)

        # Update image record
        image.ai_description = metadata['description']
        image.ai_tags = metadata['tags']
        image.ai_objects = metadata['objects']
        image.ai_scene = metadata['scene']
        image.analyzed_at = datetime.utcnow()

        await db.commit()
        await db.refresh(image)

        try:
            grouping_service = GroupingService(db)
            await grouping_service.rebuild_ai_groups()
        except Exception as exc:
            logger.warning("Failed to rebuild AI groupings: %s", exc)

        return {
            "success": True,
            "image_id": image_id,
            "analysis": {
                "description": image.ai_description,
                "tags": image.ai_tags,
                "objects": image.ai_objects,
                "scene": image.ai_scene
            }
        }

    except Exception as e:
        logger.error(f"Error analyzing image {image_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/images/batch-analyze")
async def batch_analyze_images(
    image_ids: List[int],
    db: AsyncSession = Depends(get_db)
):
    """
    Batch analyze multiple images
    """
    from sqlalchemy import select
    from datetime import datetime

    results = []

    for image_id in image_ids:
        try:
            result = await db.execute(select(Image).where(Image.id == image_id))
            image = result.scalar_one_or_none()

            if not image:
                results.append({
                    "image_id": image_id,
                    "success": False,
                    "error": "Image not found"
                })
                continue

            # Analyze
            metadata = await llava_client.extract_metadata(image.file_path)

            # Update
            image.ai_description = metadata['description']
            image.ai_tags = metadata['tags']
            image.ai_objects = metadata['objects']
            image.ai_scene = metadata['scene']
            image.analyzed_at = datetime.utcnow()

            await db.commit()

            results.append({
                "image_id": image_id,
                "success": True,
                "analysis": metadata
            })

        except Exception as e:
            logger.error(f"Error analyzing image {image_id}: {e}")
            results.append({
                "image_id": image_id,
                "success": False,
                "error": str(e)
            })

    try:
        grouping_service = GroupingService(db)
        await grouping_service.rebuild_ai_groups()
    except Exception as exc:
        logger.warning("Failed to rebuild AI groupings after batch: %s", exc)

    return {
        "total": len(image_ids),
        "succeeded": sum(1 for r in results if r.get("success")),
        "results": results
    }


# Template management endpoints
@app.get("/api/templates")
async def list_templates(db: AsyncSession = Depends(get_db)):
    """List all naming templates"""
    from sqlalchemy import select

    result = await db.execute(select(Template))
    templates = result.scalars().all()

    return {
        "templates": [
            {
                "id": t.id,
                "name": t.name,
                "pattern": t.pattern,
                "description": t.description,
                "is_default": t.is_default
            }
            for t in templates
        ],
        "predefined": {
            name: pattern
            for name, pattern in PREDEFINED_TEMPLATES.items()
        }
    }


@app.post("/api/templates")
async def create_template(
    name: str,
    pattern: str,
    description: Optional[str] = None,
    is_default: bool = False,
    db: AsyncSession = Depends(get_db)
):
    """Create new naming template"""
    # Validate template
    is_valid, message = TemplateParser.validate_template(pattern)
    if not is_valid:
        raise HTTPException(status_code=400, detail=message)

    # Create template
    template = Template(
        name=name,
        pattern=pattern,
        description=description,
        is_default=is_default
    )

    db.add(template)
    await db.commit()
    await db.refresh(template)

    return {
        "success": True,
        "template": {
            "id": template.id,
            "name": template.name,
            "pattern": template.pattern
        }
    }


class RenamePreviewRequest(BaseModel):
    template: str
    image_ids: List[int]

class RenameApplyRequest(BaseModel):
    template: str
    image_ids: List[int]
    create_backups: bool = True


class ManualGroupRequest(BaseModel):
    name: str
    description: Optional[str] = None
    image_ids: List[int] = Field(default_factory=list)


class GroupAssignmentRequest(BaseModel):
    image_ids: List[int] = Field(default_factory=list)
    replace: bool = False


class BulkTagUpdateRequest(BaseModel):
    image_ids: List[int] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)
    operation: Literal["replace", "add", "remove"] = "replace"


# Grouping endpoints
@app.get("/api/groupings")
async def get_groupings(
    group_type: Optional[GroupType] = None,
    db: AsyncSession = Depends(get_db),
):
    service = GroupingService(db)
    groups = await service.list_groups(group_type)
    return {"groups": [serialize_group_summary(summary) for summary in groups]}


@app.post("/api/groupings/rebuild")
async def rebuild_groupings(db: AsyncSession = Depends(get_db)):
    service = GroupingService(db)
    await service.rebuild_ai_groups()
    groups = await service.list_groups()
    return {"success": True, "groups": [serialize_group_summary(summary) for summary in groups]}


@app.post("/api/groupings/manual")
async def create_manual_group(
    request: ManualGroupRequest,
    db: AsyncSession = Depends(get_db),
):
    service = GroupingService(db)
    group = await service.create_manual_collection(
        name=request.name,
        description=request.description,
        image_ids=request.image_ids,
    )

    result = await db.execute(
        select(ImageGroup)
        .options(selectinload(ImageGroup.assignments))
        .where(ImageGroup.id == group.id)
    )
    persisted_group = result.scalar_one()
    return {"success": True, "group": serialize_group(persisted_group)}


@app.post("/api/groupings/{group_id}/assign")
async def assign_group_images(
    group_id: int,
    request: GroupAssignmentRequest,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(ImageGroup).where(ImageGroup.id == group_id))
    group = result.scalar_one_or_none()

    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    if group.group_type not in {GroupType.MANUAL_COLLECTION, GroupType.UPLOAD_BATCH}:
        raise HTTPException(status_code=400, detail="Group does not accept manual assignments")

    service = GroupingService(db)
    await service.assign_images_to_group(group_id, request.image_ids, replace=request.replace)
    await db.commit()

    refreshed = await db.execute(
        select(ImageGroup)
        .options(selectinload(ImageGroup.assignments))
        .where(ImageGroup.id == group_id)
    )
    persisted_group = refreshed.scalar_one()

    return {"success": True, "group": serialize_group(persisted_group)}


@app.patch("/api/images/bulk/tags")
async def bulk_update_tags(
    request: BulkTagUpdateRequest,
    db: AsyncSession = Depends(get_db),
):
    if not request.image_ids:
        raise HTTPException(status_code=400, detail="No images selected")

    normalized_tags = [tag.strip().lower() for tag in request.tags if tag.strip()]

    image_result = await db.execute(select(Image).where(Image.id.in_(request.image_ids)))
    images = image_result.scalars().all()

    if not images:
        raise HTTPException(status_code=404, detail="No matching images found")

    updated = 0
    for image in images:
        current_tags = [tag.strip().lower() for tag in (image.ai_tags or []) if tag]

        if request.operation == "replace":
            image.ai_tags = normalized_tags
        elif request.operation == "add":
            combined = list(dict.fromkeys(current_tags + normalized_tags))
            image.ai_tags = combined
        elif request.operation == "remove":
            image.ai_tags = [tag for tag in current_tags if tag not in normalized_tags]
        else:
            continue

        updated += 1

    await db.commit()

    try:
        await GroupingService(db).rebuild_ai_groups()
    except Exception as exc:
        logger.warning("Failed to rebuild groups after tag update: %s", exc)

    return {"success": True, "updated": updated}


# Rename preview and execution endpoints
@app.post("/api/rename/preview")
async def preview_rename(
    request: RenamePreviewRequest,
    db: AsyncSession = Depends(get_db)
):
    """Preview rename operation"""
    from sqlalchemy import select

    # Create rename engine
    engine = RenameEngine(template=request.template)

    previews = []

    for idx, image_id in enumerate(request.image_ids, start=1):
        result = await db.execute(select(Image).where(Image.id == image_id))
        image = result.scalar_one_or_none()

        if not image:
            continue

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
        new_filename = engine.generate_filename(metadata, index=idx, original_extension=ext)

        previews.append({
            'image_id': image_id,
            'current_filename': image.current_filename,
            'proposed_filename': new_filename,
            'metadata': metadata
        })

    return {
        "template": request.template,
        "previews": previews
    }


@app.post("/api/rename/apply")
async def apply_rename(
    request: RenameApplyRequest,
    db: AsyncSession = Depends(get_db)
):
    """Apply rename operation"""
    from sqlalchemy import select
    from datetime import datetime
    import shutil

    engine = RenameEngine(template=request.template)
    results = []

    for idx, image_id in enumerate(request.image_ids, start=1):
        result = await db.execute(select(Image).where(Image.id == image_id))
        image = result.scalar_one_or_none()

        if not image:
            results.append({
                "image_id": image_id,
                "success": False,
                "error": "Image not found"
            })
            continue

        try:
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
            new_filename = engine.generate_filename(metadata, index=idx, original_extension=ext)

            # Apply rename
            rename_result = engine.apply_rename(
                image.file_path,
                new_filename,
                create_backup=request.create_backups
            )

            if rename_result['success']:
                # Update database
                image.current_filename = new_filename
                image.file_path = rename_result['new_path']
                await db.commit()

                results.append({
                    "image_id": image_id,
                    "success": True,
                    "old_filename": Path(rename_result['old_path']).name,
                    "new_filename": new_filename
                })
            else:
                results.append({
                    "image_id": image_id,
                    "success": False,
                    "error": rename_result['error']
                })

        except Exception as e:
            logger.error(f"Error renaming image {image_id}: {e}")
            results.append({
                "image_id": image_id,
                "success": False,
                "error": str(e)
            })

    return {
        "total": len(request.image_ids),
        "succeeded": sum(1 for r in results if r.get("success")),
        "results": results
    }


@app.post("/api/rename/auto")
async def auto_rename_images(
    image_ids: List[int],
    db: AsyncSession = Depends(get_db)
):
    """
    Automatically rename images using AI with smart organization.
    Uses AI description, file metadata (date, size), and organizes into folders.
    """
    from sqlalchemy import select
    from datetime import datetime
    import os

    results = []
    base_dir = Path(settings.upload_dir)

    for image_id in image_ids:
        result = await db.execute(select(Image).where(Image.id == image_id))
        image = result.scalar_one_or_none()

        if not image:
            results.append({
                "image_id": image_id,
                "success": False,
                "error": "Image not found"
            })
            continue

        if not image.ai_description:
            results.append({
                "image_id": image_id,
                "success": False,
                "error": "Image not analyzed yet. Run AI analysis first."
            })
            continue

        try:
            # Get file metadata
            file_path = Path(image.file_path)
            file_stat = os.stat(file_path)
            file_created = datetime.fromtimestamp(file_stat.st_ctime)

            # Determine quality based on file size and dimensions
            quality = "standard"
            if image.file_size > 5_000_000:  # > 5MB
                quality = "high"
            elif image.file_size > 10_000_000:  # > 10MB
                quality = "ultra"

            if image.width and image.height:
                total_pixels = image.width * image.height
                if total_pixels > 8_000_000:  # > 8MP
                    quality = "high" if quality == "standard" else "ultra"

            # Generate smart filename from AI description
            # Take first 5-7 words from description, clean them
            desc_words = image.ai_description.lower().split()[:7]
            desc_slug = '-'.join(w.strip(',.!?') for w in desc_words if w.strip(',.!?'))
            desc_slug = desc_slug[:50]  # Limit length

            # Add quality and date
            date_str = file_created.strftime('%Y%m%d')
            ext = file_path.suffix

            # Create organized directory structure
            year = file_created.strftime('%Y')
            month = file_created.strftime('%m-%B')
            scene_type = (image.ai_scene or 'general').lower().replace(' ', '-')

            # Directory: uploads/YYYY/MM-Month/scene-type/quality/
            target_dir = base_dir / year / month / scene_type / quality
            target_dir.mkdir(parents=True, exist_ok=True)

            # Filename: description-slug_YYYYMMDD_quality.ext
            new_filename = f"{desc_slug}_{date_str}_{quality}{ext}"
            new_path = target_dir / new_filename

            # Handle duplicates
            counter = 1
            while new_path.exists():
                new_filename = f"{desc_slug}_{date_str}_{quality}_{counter}{ext}"
                new_path = target_dir / new_filename
                counter += 1

            # Move file
            file_path.rename(new_path)

            # Update database
            image.current_filename = new_filename
            image.file_path = str(new_path)
            await db.commit()

            # Get relative path for display
            rel_path = new_path.relative_to(base_dir)

            results.append({
                "image_id": image_id,
                "success": True,
                "old_filename": file_path.name,
                "new_filename": new_filename,
                "directory": str(rel_path.parent),
                "quality": quality,
                "description_used": desc_slug
            })

        except Exception as e:
            logger.error(f"Error auto-renaming image {image_id}: {e}")
            results.append({
                "image_id": image_id,
                "success": False,
                "error": str(e)
            })

    return {
        "total": len(image_ids),
        "succeeded": sum(1 for r in results if r.get("success")),
        "results": results
    }


# Storage integration endpoints
@app.post("/api/storage/nextcloud/upload")
async def upload_to_nextcloud(
    image_id: int,
    remote_path: str,
    db: AsyncSession = Depends(get_db)
):
    """Upload image to Nextcloud"""
    from sqlalchemy import select

    result = await db.execute(select(Image).where(Image.id == image_id))
    image = result.scalar_one_or_none()

    if not image:
        raise HTTPException(status_code=404, detail="Image not found")

    try:
        upload_result = await nextcloud_client.upload_file(
            image.file_path,
            remote_path
        )

        if upload_result['success']:
            image.nextcloud_path = upload_result['remote_path']
            image.storage_type = StorageType.NEXTCLOUD
            await db.commit()

        return upload_result

    except Exception as e:
        logger.error(f"Error uploading to Nextcloud: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/storage/r2/upload")
async def upload_to_r2(
    image_id: int,
    key: str,
    db: AsyncSession = Depends(get_db)
):
    """Upload image to Cloudflare R2"""
    from sqlalchemy import select

    result = await db.execute(select(Image).where(Image.id == image_id))
    image = result.scalar_one_or_none()

    if not image:
        raise HTTPException(status_code=404, detail="Image not found")

    try:
        upload_result = await r2_client.upload_file(
            image.file_path,
            key,
            metadata={
                'original_filename': image.original_filename,
                'description': image.ai_description or ''
            }
        )

        if upload_result['success']:
            image.r2_key = key
            image.storage_type = StorageType.R2
            await db.commit()

        return upload_result

    except Exception as e:
        logger.error(f"Error uploading to R2: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Image listing and serving endpoints
@app.get("/api/images")
async def list_images(db: AsyncSession = Depends(get_db)):
    """Get list of all images"""
    from sqlalchemy import select

    result = await db.execute(
        select(Image)
            .options(
                selectinload(Image.group_assignments).selectinload(ImageGroupAssociation.group),
                selectinload(Image.upload_batch),
            )
            .order_by(Image.created_at.desc())
    )
    images = result.scalars().all()

    return {
        "images": [
            {
                "id": img.id,
                "filename": img.original_filename,  # For compatibility with frontend
                "current_filename": img.current_filename,
                "file_path": img.file_path,
                "file_size": img.file_size,
                "mime_type": img.mime_type,
                "media_type": img.media_type.value if img.media_type else None,
                "width": img.width,
                "height": img.height,
                "duration_s": img.duration_s,
                "frame_rate": img.frame_rate,
                "codec": img.codec,
                "format": img.media_format,
                "metadata_id": img.metadata_id,
                "ai_description": img.ai_description,
                "ai_tags": img.ai_tags,
                "ai_objects": img.ai_objects,
                "ai_scene": img.ai_scene,
                "ai_embedding": img.ai_embedding,
                "analyzed_at": img.analyzed_at.isoformat() if img.analyzed_at else None,
                "created_at": img.created_at.isoformat() if img.created_at else None,
                "groups": [
                    {
                        "id": assignment.group.id,
                        "name": assignment.group.name,
                        "group_type": assignment.group.group_type.value,
                    }
                    for assignment in img.group_assignments
                    if assignment.group
                ],
                "upload_batch": (
                    {
                        "id": img.upload_batch.id,
                        "label": img.upload_batch.label,
                    }
                    if img.upload_batch
                    else None
                ),
            }
            for img in images
        ]
    }


@app.get("/api/images/{image_id}/thumbnail")
async def get_image_thumbnail(image_id: int, db: AsyncSession = Depends(get_db)):
    """Serve image thumbnail (or full image for now)"""
    from sqlalchemy import select

    result = await db.execute(select(Image).where(Image.id == image_id))
    image = result.scalar_one_or_none()

    if not image:
        raise HTTPException(status_code=404, detail="Image not found")

    file_path = Path(image.file_path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Image file not found")

    return FileResponse(
        path=str(file_path),
        media_type=image.mime_type,
        filename=image.current_filename
    )


# Serve frontend static files
static_dir = Path(__file__).parent / "static"
if static_dir.exists():
    app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="static")


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug
    )
