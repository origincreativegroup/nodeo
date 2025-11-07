"""jspow - AI-powered image file renaming and organization tool
Main FastAPI application"""
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional
import time

from fastapi import BackgroundTasks, Depends, FastAPI, File, HTTPException, UploadFile, Request
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
    Project,
    ProjectType,
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
    metadata_service,
    AssetType,
)
from app.services.project_service import ProjectService
from app.services.error_handler import create_error_response, log_detailed_error
from app.services.project_rename import ProjectRenameService
from app.ai.project_classifier import ProjectClassifier
from app.storage.nextcloud_sync import NextcloudSyncService
from app.storage import nextcloud_client, r2_client, stream_client, storage_manager, metadata_sidecar_writer

# Configure enhanced logging
from app.debug_utils import setup_enhanced_logging, RequestLogger
setup_enhanced_logging(log_level="DEBUG" if settings.debug else "INFO")
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


# Request/Response logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all HTTP requests and responses with timing"""
    start_time = time.time()

    # Process request
    try:
        response = await call_next(request)
        duration_ms = (time.time() - start_time) * 1000

        # Log successful request
        RequestLogger.log_request(
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=duration_ms
        )

        return response
    except Exception as e:
        duration_ms = (time.time() - start_time) * 1000

        # Log failed request
        RequestLogger.log_error(
            method=request.method,
            path=request.url.path,
            error=e
        )

        raise


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "app": settings.app_name,
        "version": settings.app_version
    }


# Debug and monitoring endpoints
@app.get("/debug/system")
async def debug_system_info(db: AsyncSession = Depends(get_db)):
    """Get comprehensive system debug information"""
    from app.debug_utils import DebugInfo

    system_info = DebugInfo.get_system_info()
    env_info = DebugInfo.get_environment_info()
    storage_info = await DebugInfo.get_storage_info()
    db_stats = await DebugInfo.get_database_stats(db)

    return {
        "timestamp": datetime.utcnow().isoformat(),
        "system": system_info,
        "environment": env_info,
        "storage": storage_info,
        "database": db_stats,
    }


@app.get("/debug/health-full")
async def full_health_check(db: AsyncSession = Depends(get_db)):
    """Comprehensive health check with all service connections"""
    from app.debug_utils import DebugInfo

    results = {
        "timestamp": datetime.utcnow().isoformat(),
        "overall_status": "healthy",
        "services": {}
    }

    # Check database
    db_status = await DebugInfo.check_database_connection(db)
    results["services"]["database"] = db_status
    if db_status["status"] != "connected":
        results["overall_status"] = "degraded"

    # Check Ollama
    ollama_status = await DebugInfo.check_ollama_connection()
    results["services"]["ollama"] = ollama_status
    if ollama_status["status"] != "connected":
        results["overall_status"] = "degraded"

    # Check Nextcloud
    nextcloud_status = await DebugInfo.check_nextcloud_connection()
    results["services"]["nextcloud"] = nextcloud_status
    if nextcloud_status["status"] != "connected":
        results["overall_status"] = "degraded"

    # Get database stats
    db_stats = await DebugInfo.get_database_stats(db)
    results["database_stats"] = db_stats

    return results


@app.get("/debug/logs/recent")
async def get_recent_logs(lines: int = 50):
    """Get recent log entries"""
    try:
        log_file = Path("logs/jspow.log")
        if not log_file.exists():
            return {"error": "Log file not found", "logs": []}

        with open(log_file, "r") as f:
            all_lines = f.readlines()
            recent_lines = all_lines[-lines:]

        return {
            "total_lines": len(all_lines),
            "showing": len(recent_lines),
            "logs": [line.strip() for line in recent_lines]
        }
    except Exception as e:
        logger.error(f"Error reading logs: {e}")
        return {"error": str(e), "logs": []}


@app.get("/debug/errors/recent")
async def get_recent_errors(lines: int = 50):
    """Get recent error log entries"""
    try:
        error_log = Path("logs/errors.log")
        if not error_log.exists():
            return {"error": "Error log file not found", "errors": []}

        with open(error_log, "r") as f:
            all_lines = f.readlines()
            recent_lines = all_lines[-lines:]

        return {
            "total_errors": len(all_lines),
            "showing": len(recent_lines),
            "errors": [line.strip() for line in recent_lines]
        }
    except Exception as e:
        logger.error(f"Error reading error log: {e}")
        return {"error": str(e), "errors": []}


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

        # Generate smart filename suggestion
        try:
            context = {'date': datetime.now().strftime("%Y%m%d")}
            suggested_base = await llava_client.generate_filename(
                image.file_path,
                metadata=metadata,
                context=context
            )
            from pathlib import Path
            extension = Path(image.current_filename).suffix
            from app.services import filename_service
            suggested_filename = await filename_service.suggest_unique_name(
                suggested_base,
                extension,
                None,  # No folder context
                db,
                exclude_image_id=image.id
            )
            image.suggested_filename = suggested_filename
        except Exception as e:
            logger.warning(f"Failed to generate suggested filename: {e}")

        await db.commit()
        await db.refresh(image)

        # Run AI grouping
        try:
            grouping_service = GroupingService(db)
            await grouping_service.rebuild_ai_groups()
        except Exception as exc:
            logger.warning("Failed to rebuild AI groupings: %s", exc)

        # Run project classification
        project_classification = None
        try:
            classifier = ProjectClassifier(db, llava_client)
            classification_result = await classifier.classify_image(
                image=image,
                auto_assign=True,
            )
            project_classification = {
                "assigned_project_id": classification_result.assigned_project_id,
                "assigned_project_name": classification_result.assigned_project_name,
                "confidence": classification_result.confidence,
                "requires_review": classification_result.requires_review,
                "reasons": classification_result.reasons,
                "top_matches": [
                    {
                        "project_id": match.project_id,
                        "project_name": match.project_name,
                        "confidence": match.confidence,
                        "reasons": match.reasons,
                    }
                    for match in classification_result.all_matches[:3]
                ],
            }
        except Exception as exc:
            logger.warning("Failed to classify project: %s", exc)

        return {
            "success": True,
            "image_id": image_id,
            "analysis": {
                "description": image.ai_description,
                "tags": image.ai_tags,
                "objects": image.ai_objects,
                "scene": image.ai_scene
            },
            "suggested_filename": image.suggested_filename,
            "project_classification": project_classification,
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
    Batch analyze multiple images using concurrent processing for improved performance
    """
    from sqlalchemy import select
    from datetime import datetime

    # Bulk load all images at once (single query instead of N queries)
    result = await db.execute(select(Image).where(Image.id.in_(image_ids)))
    images = result.scalars().all()

    # Create lookup maps
    image_by_id = {img.id: img for img in images}
    image_by_path = {img.file_path: img for img in images}

    # Track missing images
    results = []
    found_image_ids = set(image_by_id.keys())
    missing_image_ids = set(image_ids) - found_image_ids

    for image_id in missing_image_ids:
        results.append({
            "image_id": image_id,
            "success": False,
            "error": "Image not found"
        })

    # Get paths for concurrent analysis
    image_paths = [img.file_path for img in images]

    if not image_paths:
        return {
            "total": len(image_ids),
            "succeeded": 0,
            "results": results,
            "project_classifications": [],
        }

    # Use concurrent batch analysis (5x faster!)
    try:
        analysis_results = await llava_client.batch_analyze(
            image_paths=image_paths,
            extract_full_metadata=True,
            concurrent=True,
            max_concurrent=5  # Process 5 images simultaneously
        )

        # Batch update all images (single transaction)
        now = datetime.utcnow()
        successful_image_ids = []

        for analysis in analysis_results:
            image_path = analysis.get('image_path')

            if 'error' in analysis:
                # Find image ID from path
                image = image_by_path.get(image_path)
                results.append({
                    "image_id": image.id if image else None,
                    "success": False,
                    "error": analysis['error']
                })
                continue

            # Update image metadata
            image = image_by_path.get(image_path)
            if image:
                image.ai_description = analysis.get('description', '')
                image.ai_tags = analysis.get('tags', [])
                image.ai_objects = analysis.get('objects', [])
                image.ai_scene = analysis.get('scene', '')
                image.analyzed_at = now

                successful_image_ids.append(image.id)

                # Generate smart filename suggestion
                suggested_filename = None
                try:
                    context = {'date': datetime.now().strftime("%Y%m%d")}
                    suggested_base = await llava_client.generate_filename(
                        image.file_path,
                        metadata=analysis,
                        context=context
                    )
                    extension = Path(image.current_filename).suffix
                    from app.services import filename_service
                    suggested_filename = await filename_service.suggest_unique_name(
                        suggested_base,
                        extension,
                        None,
                        db,
                        exclude_image_id=image.id
                    )
                    image.suggested_filename = suggested_filename
                except Exception as e:
                    logger.warning(f"Failed to generate suggested filename for {image.id}: {e}")

                results.append({
                    "image_id": image.id,
                    "success": True,
                    "analysis": {
                        "description": analysis.get('description', ''),
                        "tags": analysis.get('tags', []),
                        "objects": analysis.get('objects', []),
                        "scene": analysis.get('scene', '')
                    },
                    "suggested_filename": suggested_filename
                })

        # Single commit for all updates (instead of N commits)
        await db.commit()

    except Exception as e:
        logger.error(f"Error during batch analysis: {e}")
        await db.rollback()
        # Mark all remaining as failed
        for img in images:
            if img.id not in [r.get("image_id") for r in results]:
                results.append({
                    "image_id": img.id,
                    "success": False,
                    "error": str(e)
                })
        successful_image_ids = []

    # Rebuild AI groups
    try:
        grouping_service = GroupingService(db)
        await grouping_service.rebuild_ai_groups()
    except Exception as exc:
        logger.warning("Failed to rebuild AI groupings after batch: %s", exc)

    # Run batch project classification
    project_classifications = []
    if successful_image_ids:
        try:
            classifier = ProjectClassifier(db, llava_client)
            classification_results = await classifier.classify_batch(
                image_ids=successful_image_ids,
                auto_assign=True,
            )
            project_classifications = [
                {
                    "image_id": cr.image_id,
                    "assigned_project_id": cr.assigned_project_id,
                    "assigned_project_name": cr.assigned_project_name,
                    "confidence": cr.confidence,
                    "requires_review": cr.requires_review,
                }
                for cr in classification_results
            ]
        except Exception as exc:
            logger.warning("Failed to classify projects after batch: %s", exc)

    return {
        "total": len(image_ids),
        "succeeded": sum(1 for r in results if r.get("success")),
        "results": results,
        "project_classifications": project_classifications,
    }


# Smart Rename endpoints
class SuggestNameRequest(BaseModel):
    """Request for smart name suggestion"""
    folder_id: Optional[int] = None
    context: Optional[Dict[str, Any]] = Field(default_factory=dict)


@app.post("/api/images/{image_id}/suggest-name")
async def suggest_smart_name(
    image_id: int,
    request: SuggestNameRequest,
    db: AsyncSession = Depends(get_db)
):
    """Generate LLaVA-powered smart filename suggestion"""
    try:
        # Load image from database
        stmt = select(Image).where(Image.id == image_id)
        result = await db.execute(stmt)
        image = result.scalar_one_or_none()

        if not image:
            raise HTTPException(status_code=404, detail="Image not found")

        # Build metadata dict from AI analysis
        metadata = {
            'description': image.ai_description or '',
            'tags': image.ai_tags or [],
            'objects': image.ai_objects or [],
            'scene': image.ai_scene or '',
        }

        # Check if image has been analyzed
        if not image.ai_description:
            return {
                "success": False,
                "error": "Image not analyzed yet",
                "requires_analysis": True
            }

        # Build context for filename generation
        from datetime import datetime
        context = request.context or {}
        context['date'] = datetime.now().strftime("%Y%m%d")

        # If folder_id provided, get folder context
        if request.folder_id:
            folder_stmt = select(ImageGroup).where(ImageGroup.id == request.folder_id)
            folder_result = await db.execute(folder_stmt)
            folder = folder_result.scalar_one_or_none()

            if folder:
                context['folder_type'] = folder.group_type.value
                context['folder_name'] = folder.name

                # Add project context if applicable
                if folder.project_id:
                    project_stmt = select(Project).where(Project.id == folder.project_id)
                    project_result = await db.execute(project_stmt)
                    project = project_result.scalar_one_or_none()
                    if project:
                        context['project_name'] = project.name

        # Generate smart filename
        suggested_base = await llava_client.generate_filename(
            image.file_path,
            metadata=metadata,
            context=context
        )

        # Get file extension
        from pathlib import Path
        extension = Path(image.current_filename).suffix

        # Check for conflicts and ensure uniqueness
        from app.services import filename_service
        suggested_filename = await filename_service.suggest_unique_name(
            suggested_base,
            extension,
            request.folder_id,
            db,
            exclude_image_id=image_id
        )

        # Update image with suggested filename
        image.suggested_filename = suggested_filename
        await db.commit()

        return {
            "success": True,
            "suggested_filename": suggested_filename,
            "current_filename": image.current_filename,
            "metadata_used": metadata
        }

    except Exception as e:
        logger.error(f"Error suggesting name for image {image_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class BatchSuggestNamesRequest(BaseModel):
    """Request for batch name suggestions"""
    image_ids: List[int]
    folder_id: Optional[int] = None
    context: Optional[Dict[str, Any]] = Field(default_factory=dict)


@app.post("/api/images/batch-suggest-names")
async def batch_suggest_names(
    request: BatchSuggestNamesRequest,
    db: AsyncSession = Depends(get_db)
):
    """Generate smart name suggestions for multiple images concurrently"""
    try:
        from datetime import datetime
        import asyncio

        # Load all images
        stmt = select(Image).where(Image.id.in_(request.image_ids))
        result = await db.execute(stmt)
        images = result.scalars().all()

        if not images:
            raise HTTPException(status_code=404, detail="No images found")

        # Get folder context if provided
        folder_context = {}
        if request.folder_id:
            folder_stmt = select(ImageGroup).where(ImageGroup.id == request.folder_id)
            folder_result = await db.execute(folder_stmt)
            folder = folder_result.scalar_one_or_none()

            if folder:
                folder_context['folder_type'] = folder.group_type.value
                folder_context['folder_name'] = folder.name

                if folder.project_id:
                    project_stmt = select(Project).where(Project.id == folder.project_id)
                    project_result = await db.execute(project_stmt)
                    project = project_result.scalar_one_or_none()
                    if project:
                        folder_context['project_name'] = project.name

        # Generate suggestions concurrently
        suggestions = []

        async def generate_suggestion(image: Image, index: int):
            try:
                # Skip if not analyzed
                if not image.ai_description:
                    return {
                        "image_id": image.id,
                        "success": False,
                        "error": "Not analyzed",
                        "requires_analysis": True
                    }

                metadata = {
                    'description': image.ai_description or '',
                    'tags': image.ai_tags or [],
                    'objects': image.ai_objects or [],
                    'scene': image.ai_scene or '',
                }

                context = {**folder_context, **request.context}
                context['date'] = datetime.now().strftime("%Y%m%d")
                context['index'] = index + 1

                suggested_base = await llava_client.generate_filename(
                    image.file_path,
                    metadata=metadata,
                    context=context
                )

                from pathlib import Path
                extension = Path(image.current_filename).suffix

                from app.services import filename_service
                suggested_filename = await filename_service.suggest_unique_name(
                    suggested_base,
                    extension,
                    request.folder_id,
                    db,
                    exclude_image_id=image.id
                )

                # Update image
                image.suggested_filename = suggested_filename

                return {
                    "image_id": image.id,
                    "success": True,
                    "suggested_filename": suggested_filename,
                    "current_filename": image.current_filename
                }

            except Exception as e:
                logger.error(f"Error generating suggestion for image {image.id}: {e}")
                return {
                    "image_id": image.id,
                    "success": False,
                    "error": str(e)
                }

        # Process with semaphore to limit concurrency
        semaphore = asyncio.Semaphore(5)

        async def process_with_limit(img, idx):
            async with semaphore:
                return await generate_suggestion(img, idx)

        suggestions = await asyncio.gather(
            *[process_with_limit(img, i) for i, img in enumerate(images)]
        )

        await db.commit()

        return {
            "success": True,
            "total": len(request.image_ids),
            "suggestions": suggestions
        }

    except Exception as e:
        logger.error(f"Error in batch suggest names: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class QuickRenameRequest(BaseModel):
    """Request for quick rename"""
    new_filename: str


@app.post("/api/images/{image_id}/quick-rename")
async def quick_rename_image(
    image_id: int,
    request: QuickRenameRequest,
    db: AsyncSession = Depends(get_db)
):
    """Quick rename with automatic backup"""
    try:
        from pathlib import Path
        import shutil

        # Load image
        stmt = select(Image).where(Image.id == image_id)
        result = await db.execute(stmt)
        image = result.scalar_one_or_none()

        if not image:
            raise HTTPException(status_code=404, detail="Image not found")

        # Sanitize new filename
        from app.services import filename_service
        new_filename = filename_service.sanitize_filename(request.new_filename)

        # Get current file paths
        old_path = Path(image.file_path)
        new_path = old_path.parent / new_filename

        # Check if file already exists
        if new_path.exists() and new_path != old_path:
            raise HTTPException(
                status_code=400,
                detail=f"File {new_filename} already exists"
            )

        # Create backup
        backup_path = old_path.parent / f".backup_{old_path.name}"
        shutil.copy2(old_path, backup_path)

        try:
            # Rename file on disk
            old_path.rename(new_path)

            # Update database
            image.current_filename = new_filename
            image.file_path = str(new_path)
            image.filename_accepted = (new_filename == image.suggested_filename)
            image.last_renamed_at = datetime.now()

            await db.commit()

            # Remove backup on success
            backup_path.unlink()

            return {
                "success": True,
                "new_filename": new_filename,
                "old_filename": image.current_filename
            }

        except Exception as e:
            # Restore from backup on error
            if backup_path.exists():
                shutil.copy2(backup_path, old_path)
                backup_path.unlink()
            raise e

    except Exception as e:
        logger.error(f"Error in quick rename for image {image_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Template management endpoints
@app.get("/api/templates")
async def list_templates(
    category: Optional[str] = None,
    favorites_only: bool = False,
    db: AsyncSession = Depends(get_db)
):
    """List all naming templates with optional filtering"""
    from sqlalchemy import select

    # Build query with filters
    query = select(Template)
    if category:
        query = query.filter(Template.category == category)
    if favorites_only:
        query = query.filter(Template.is_favorite == True)

    result = await db.execute(query)
    templates = result.scalars().all()

    return {
        "templates": [
            {
                "id": t.id,
                "name": t.name,
                "pattern": t.pattern,
                "description": t.description,
                "is_default": t.is_default,
                "is_favorite": t.is_favorite,
                "category": t.category,
                "usage_count": t.usage_count,
                "variables_used": t.variables_used
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
    category: str = "custom",
    is_favorite: bool = False,
    db: AsyncSession = Depends(get_db)
):
    """Create new naming template"""
    # Validate template
    is_valid, message = TemplateParser.validate_template(pattern)
    if not is_valid:
        raise HTTPException(status_code=400, detail=message)

    # Extract variables from pattern
    parser = TemplateParser(pattern)
    variables_used = parser.variables

    # Create template
    template = Template(
        name=name,
        pattern=pattern,
        description=description,
        is_default=is_default,
        is_favorite=is_favorite,
        category=category,
        usage_count=0,
        variables_used=variables_used
    )

    db.add(template)
    await db.commit()
    await db.refresh(template)

    return {
        "success": True,
        "template": {
            "id": template.id,
            "name": template.name,
            "pattern": template.pattern,
            "description": template.description,
            "is_favorite": template.is_favorite,
            "category": template.category,
            "variables_used": template.variables_used
        }
    }


@app.get("/api/templates/{template_id}")
async def get_template(template_id: int, db: AsyncSession = Depends(get_db)):
    """Get a specific template by ID"""
    from sqlalchemy import select

    result = await db.execute(select(Template).filter(Template.id == template_id))
    template = result.scalar_one_or_none()

    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    return {
        "id": template.id,
        "name": template.name,
        "pattern": template.pattern,
        "description": template.description,
        "is_default": template.is_default,
        "is_favorite": template.is_favorite,
        "category": template.category,
        "usage_count": template.usage_count,
        "variables_used": template.variables_used,
        "created_at": template.created_at,
        "updated_at": template.updated_at
    }


@app.put("/api/templates/{template_id}")
async def update_template(
    template_id: int,
    name: Optional[str] = None,
    pattern: Optional[str] = None,
    description: Optional[str] = None,
    is_favorite: Optional[bool] = None,
    category: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """Update an existing template"""
    from sqlalchemy import select

    result = await db.execute(select(Template).filter(Template.id == template_id))
    template = result.scalar_one_or_none()

    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    # Update fields if provided
    if name is not None:
        template.name = name
    if pattern is not None:
        # Validate new pattern
        is_valid, message = TemplateParser.validate_template(pattern)
        if not is_valid:
            raise HTTPException(status_code=400, detail=message)
        template.pattern = pattern
        # Update variables_used
        parser = TemplateParser(pattern)
        template.variables_used = parser.variables
    if description is not None:
        template.description = description
    if is_favorite is not None:
        template.is_favorite = is_favorite
    if category is not None:
        template.category = category

    await db.commit()
    await db.refresh(template)

    return {
        "success": True,
        "template": {
            "id": template.id,
            "name": template.name,
            "pattern": template.pattern,
            "description": template.description,
            "is_favorite": template.is_favorite,
            "category": template.category,
            "variables_used": template.variables_used
        }
    }


@app.delete("/api/templates/{template_id}")
async def delete_template(template_id: int, db: AsyncSession = Depends(get_db)):
    """Delete a template"""
    from sqlalchemy import select

    result = await db.execute(select(Template).filter(Template.id == template_id))
    template = result.scalar_one_or_none()

    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    await db.delete(template)
    await db.commit()

    return {"success": True, "message": "Template deleted"}


@app.post("/api/templates/{template_id}/favorite")
async def toggle_favorite_template(template_id: int, db: AsyncSession = Depends(get_db)):
    """Toggle favorite status of a template"""
    from sqlalchemy import select

    result = await db.execute(select(Template).filter(Template.id == template_id))
    template = result.scalar_one_or_none()

    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    template.is_favorite = not template.is_favorite
    await db.commit()
    await db.refresh(template)

    return {
        "success": True,
        "is_favorite": template.is_favorite
    }


@app.post("/api/templates/import")
async def import_templates(templates_data: List[dict], db: AsyncSession = Depends(get_db)):
    """Import multiple templates from JSON"""
    imported = []
    errors = []

    for template_data in templates_data:
        try:
            # Validate required fields
            if "name" not in template_data or "pattern" not in template_data:
                errors.append({"error": "Missing required fields", "data": template_data})
                continue

            # Validate template pattern
            is_valid, message = TemplateParser.validate_template(template_data["pattern"])
            if not is_valid:
                errors.append({"error": message, "data": template_data})
                continue

            # Extract variables
            parser = TemplateParser(template_data["pattern"])
            variables_used = parser.variables

            # Create template
            template = Template(
                name=template_data["name"],
                pattern=template_data["pattern"],
                description=template_data.get("description"),
                is_favorite=template_data.get("is_favorite", False),
                category=template_data.get("category", "custom"),
                usage_count=0,
                variables_used=variables_used
            )

            db.add(template)
            imported.append(template_data["name"])

        except Exception as e:
            errors.append({"error": str(e), "data": template_data})

    if imported:
        await db.commit()

    return {
        "success": True,
        "imported_count": len(imported),
        "imported": imported,
        "errors": errors
    }


@app.get("/api/templates/export")
async def export_templates(db: AsyncSession = Depends(get_db)):
    """Export all custom templates as JSON"""
    from sqlalchemy import select

    result = await db.execute(select(Template))
    templates = result.scalars().all()

    export_data = [
        {
            "name": t.name,
            "pattern": t.pattern,
            "description": t.description,
            "category": t.category,
            "is_favorite": t.is_favorite,
            "variables_used": t.variables_used
        }
        for t in templates
    ]

    return {
        "templates": export_data,
        "count": len(export_data)
    }


class RenamePreviewRequest(BaseModel):
    template: str
    image_ids: List[int]

class RenameApplyRequest(BaseModel):
    template: str
    image_ids: List[int]
    create_backups: bool = True


class BulkRenameRequest(BaseModel):
    image_ids: List[int]
    find: str
    replace: str
    use_regex: bool = False
    case_sensitive: bool = False
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


class FeedbackRequest(BaseModel):
    type: Literal["bug", "feature", "improvement", "other"]
    title: str
    description: str
    stepsToReproduce: Optional[str] = None
    email: Optional[str] = None
    sentiment: Optional[Literal["positive", "negative"]] = None
    systemInfo: Optional[Dict[str, Any]] = None
    isErrorReport: bool = False


class ErrorLogRequest(BaseModel):
    title: str
    message: str
    category: str
    severity: str
    technicalDetails: Optional[str] = None
    timestamp: str
    context: Optional[Dict[str, Any]] = None
    userAgent: Optional[str] = None
    url: Optional[str] = None


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


# Folder Management endpoints (unified folder API for groups)
@app.get("/api/folders")
async def list_folders(
    include_children: bool = True,
    db: AsyncSession = Depends(get_db)
):
    """List all folders/groups with optional hierarchy"""
    try:
        stmt = select(ImageGroup).options(selectinload(ImageGroup.assignments))

        result = await db.execute(stmt)
        groups = result.scalars().all()

        # Build folder tree if include_children
        folders = []
        for group in groups:
            folder_dict = serialize_group(group)

            # Add hierarchy info
            folder_dict['parent_id'] = group.parent_id
            folder_dict['sort_order'] = group.sort_order

            # Get children if requested
            if include_children:
                children_stmt = select(ImageGroup).where(
                    ImageGroup.parent_id == group.id
                ).options(selectinload(ImageGroup.assignments))

                children_result = await db.execute(children_stmt)
                children = children_result.scalars().all()

                folder_dict['children'] = [
                    {
                        **serialize_group(child),
                        'parent_id': child.parent_id,
                        'sort_order': child.sort_order
                    }
                    for child in children
                ]
            else:
                folder_dict['children'] = []

            folders.append(folder_dict)

        return {"folders": folders}

    except Exception as e:
        logger.error(f"Error listing folders: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class CreateFolderRequest(BaseModel):
    """Request to create a new folder"""
    name: str
    description: Optional[str] = None
    parent_id: Optional[int] = None
    image_ids: Optional[List[int]] = Field(default_factory=list)


@app.post("/api/folders")
async def create_folder(
    request: CreateFolderRequest,
    db: AsyncSession = Depends(get_db)
):
    """Create a new manual folder/collection"""
    try:
        # Create new ImageGroup as manual collection
        folder = ImageGroup(
            name=request.name,
            description=request.description,
            group_type=GroupType.MANUAL_COLLECTION,
            is_user_defined=True,
            parent_id=request.parent_id,
            sort_order=0,
            attributes={}
        )

        db.add(folder)
        await db.flush()  # Get the ID

        # Add images if provided
        if request.image_ids:
            service = GroupingService(db)
            await service.assign_images_to_group(
                folder.id,
                request.image_ids,
                replace=False
            )

        await db.commit()
        await db.refresh(folder)

        # Load with assignments
        stmt = (
            select(ImageGroup)
            .options(selectinload(ImageGroup.assignments))
            .where(ImageGroup.id == folder.id)
        )
        result = await db.execute(stmt)
        persisted = result.scalar_one()

        return {
            "success": True,
            "folder": {
                **serialize_group(persisted),
                'parent_id': persisted.parent_id,
                'sort_order': persisted.sort_order
            }
        }

    except Exception as e:
        logger.error(f"Error creating folder: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class UpdateFolderRequest(BaseModel):
    """Request to update a folder"""
    name: Optional[str] = None
    description: Optional[str] = None
    parent_id: Optional[int] = None
    sort_order: Optional[int] = None


@app.put("/api/folders/{folder_id}")
async def update_folder(
    folder_id: int,
    request: UpdateFolderRequest,
    db: AsyncSession = Depends(get_db)
):
    """Update folder name, description, or hierarchy"""
    try:
        stmt = select(ImageGroup).where(ImageGroup.id == folder_id)
        result = await db.execute(stmt)
        folder = result.scalar_one_or_none()

        if not folder:
            raise HTTPException(status_code=404, detail="Folder not found")

        # Only allow updating manual collections
        if folder.group_type != GroupType.MANUAL_COLLECTION:
            raise HTTPException(
                status_code=400,
                detail="Can only update manual folders"
            )

        # Update fields
        if request.name is not None:
            folder.name = request.name
        if request.description is not None:
            folder.description = request.description
        if request.parent_id is not None:
            # Prevent circular references
            if request.parent_id == folder_id:
                raise HTTPException(
                    status_code=400,
                    detail="Folder cannot be its own parent"
                )
            folder.parent_id = request.parent_id
        if request.sort_order is not None:
            folder.sort_order = request.sort_order

        await db.commit()
        await db.refresh(folder)

        return {
            "success": True,
            "folder": {
                **serialize_group(folder),
                'parent_id': folder.parent_id,
                'sort_order': folder.sort_order
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating folder {folder_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/folders/{folder_id}")
async def delete_folder(
    folder_id: int,
    delete_children: bool = False,
    db: AsyncSession = Depends(get_db)
):
    """Delete a folder/group"""
    try:
        stmt = select(ImageGroup).where(ImageGroup.id == folder_id)
        result = await db.execute(stmt)
        folder = result.scalar_one_or_none()

        if not folder:
            raise HTTPException(status_code=404, detail="Folder not found")

        # Only allow deleting manual collections
        if folder.group_type != GroupType.MANUAL_COLLECTION:
            raise HTTPException(
                status_code=400,
                detail="Can only delete manual folders"
            )

        # Check for children
        if not delete_children:
            children_stmt = select(ImageGroup).where(
                ImageGroup.parent_id == folder_id
            )
            children_result = await db.execute(children_stmt)
            children = children_result.scalars().all()

            if children:
                raise HTTPException(
                    status_code=400,
                    detail=f"Folder has {len(children)} subfolders. Set delete_children=true to delete them."
                )

        # Delete folder (cascade will handle children and associations)
        await db.delete(folder)
        await db.commit()

        return {"success": True, "message": f"Folder {folder_id} deleted"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting folder {folder_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class AddImagesToFolderRequest(BaseModel):
    """Request to add images to a folder"""
    image_ids: List[int]


@app.post("/api/folders/{folder_id}/images")
async def add_images_to_folder(
    folder_id: int,
    request: AddImagesToFolderRequest,
    db: AsyncSession = Depends(get_db)
):
    """Add images to a folder"""
    try:
        stmt = select(ImageGroup).where(ImageGroup.id == folder_id)
        result = await db.execute(stmt)
        folder = result.scalar_one_or_none()

        if not folder:
            raise HTTPException(status_code=404, detail="Folder not found")

        service = GroupingService(db)
        await service.assign_images_to_group(
            folder_id,
            request.image_ids,
            replace=False
        )
        await db.commit()

        return {
            "success": True,
            "added": len(request.image_ids),
            "folder_id": folder_id
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding images to folder {folder_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/folders/{folder_id}/images/{image_id}")
async def remove_image_from_folder(
    folder_id: int,
    image_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Remove a specific image from a folder"""
    try:
        # Find association
        stmt = select(ImageGroupAssociation).where(
            ImageGroupAssociation.group_id == folder_id,
            ImageGroupAssociation.image_id == image_id
        )
        result = await db.execute(stmt)
        association = result.scalar_one_or_none()

        if not association:
            raise HTTPException(
                status_code=404,
                detail="Image not in this folder"
            )

        await db.delete(association)
        await db.commit()

        return {
            "success": True,
            "message": f"Image {image_id} removed from folder {folder_id}"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error removing image from folder: {e}")
        raise HTTPException(status_code=500, detail=str(e))


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


class MetadataUpdateRequest(BaseModel):
    title: str
    description: str
    alt_text: str
    tags: List[str] = []


class ProjectCreateRequest(BaseModel):
    name: str
    project_type: ProjectType = ProjectType.PERSONAL
    description: Optional[str] = None
    ai_keywords: Optional[List[str]] = None
    visual_themes: Optional[Dict[str, Any]] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    nextcloud_folder: Optional[str] = None
    default_naming_template: Optional[str] = None
    portfolio_metadata: Optional[Dict[str, Any]] = None
    featured_on_portfolio: bool = False


class ProjectUpdateRequest(BaseModel):
    name: Optional[str] = None
    project_type: Optional[ProjectType] = None
    description: Optional[str] = None
    ai_keywords: Optional[List[str]] = None
    visual_themes: Optional[Dict[str, Any]] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    nextcloud_folder: Optional[str] = None
    default_naming_template: Optional[str] = None
    portfolio_metadata: Optional[Dict[str, Any]] = None
    featured_on_portfolio: Optional[bool] = None
    is_active: Optional[bool] = None


class ProjectAssignImagesRequest(BaseModel):
    image_ids: List[int]
    replace: bool = False


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

        asset_type = (
            AssetType.VIDEO
            if image.mime_type and image.mime_type.startswith("video/")
            else AssetType.IMAGE
        )

        sidecar_metadata = metadata_sidecar_writer.load(image.file_path)
        if sidecar_metadata:
            enriched_metadata = metadata_service.ensure_metadata_shape(
                {**sidecar_metadata, 'source': 'sidecar'},
                asset_type,
                default_source='sidecar',
            )
            sidecar_exists = True
        else:
            enriched_metadata = await metadata_service.generate_metadata(
                image.file_path,
                asset_type=asset_type,
                existing={
                    'description': image.ai_description,
                    'tags': image.ai_tags,
                    'alt_text': None,
                },
            )
            sidecar_exists = False

        metadata = {
            'description': enriched_metadata.get('description') or image.ai_description or '',
            'tags': enriched_metadata.get('tags') or image.ai_tags or [],
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
            'metadata': enriched_metadata,
            'sidecar_exists': sidecar_exists,
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


@app.post("/api/rename/bulk")
async def bulk_rename(
    request: BulkRenameRequest,
    db: AsyncSession = Depends(get_db)
):
    """Apply bulk find/replace rename operation"""
    from sqlalchemy import select
    import re
    import shutil
    from pathlib import Path

    results = []

    if not request.find:
        raise HTTPException(status_code=400, detail="Find pattern cannot be empty")

    for image_id in request.image_ids:
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
            current_filename = image.current_filename
            old_path = Path(image.file_path)

            # Apply find/replace based on settings
            new_filename = current_filename

            if request.use_regex:
                try:
                    flags = 0 if request.case_sensitive else re.IGNORECASE
                    new_filename = re.sub(request.find, request.replace, current_filename, flags=flags)
                except re.error as e:
                    results.append({
                        "image_id": image_id,
                        "success": False,
                        "error": f"Invalid regex pattern: {str(e)}"
                    })
                    continue
            else:
                if request.case_sensitive:
                    new_filename = current_filename.replace(request.find, request.replace)
                else:
                    # Case-insensitive replacement
                    pattern = re.escape(request.find)
                    new_filename = re.sub(pattern, request.replace, current_filename, flags=re.IGNORECASE)

            # Skip if filename didn't change
            if new_filename == current_filename:
                results.append({
                    "image_id": image_id,
                    "success": True,
                    "old_filename": current_filename,
                    "new_filename": current_filename
                })
                continue

            # Create new path
            new_path = old_path.parent / new_filename

            # Check if target file already exists
            if new_path.exists():
                results.append({
                    "image_id": image_id,
                    "success": False,
                    "error": f"File already exists: {new_filename}"
                })
                continue

            # Create backup if requested
            if request.create_backups:
                backup_path = old_path.parent / f"{current_filename}.backup"
                shutil.copy2(old_path, backup_path)

            # Rename file
            old_path.rename(new_path)

            # Update database
            image.current_filename = new_filename
            image.file_path = str(new_path)
            await db.commit()

            results.append({
                "image_id": image_id,
                "success": True,
                "old_filename": current_filename,
                "new_filename": new_filename
            })

        except Exception as e:
            logger.error(f"Error bulk renaming image {image_id}: {e}")
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


@app.post("/api/metadata/{image_id}/sidecar")
async def save_metadata_sidecar(
    image_id: int,
    request: MetadataUpdateRequest,
    db: AsyncSession = Depends(get_db),
):
    """Persist curated metadata to a JSON sidecar file."""

    from sqlalchemy import select

    result = await db.execute(select(Image).where(Image.id == image_id))
    image = result.scalar_one_or_none()

    if not image:
        raise HTTPException(status_code=404, detail="Image not found")

    asset_type = (
        AssetType.VIDEO
        if image.mime_type and image.mime_type.startswith("video/")
        else AssetType.IMAGE
    )

    normalized_metadata = metadata_service.ensure_metadata_shape(
        {
            'title': request.title,
            'description': request.description,
            'alt_text': request.alt_text,
            'tags': request.tags,
            'source': 'sidecar',
        },
        asset_type,
        default_source='sidecar',
    )

    try:
        sidecar_path = metadata_sidecar_writer.write(
            image.file_path,
            normalized_metadata,
        )
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Asset file not found")

    image.ai_description = normalized_metadata['description']
    image.ai_tags = normalized_metadata['tags']
    await db.commit()
    await db.refresh(image)

    return {
        "success": True,
        "image_id": image_id,
        "sidecar_path": str(sidecar_path),
        "metadata": normalized_metadata,
    }


@app.get("/api/metadata/{image_id}/sidecar")
async def download_metadata_sidecar(
    image_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Download the metadata sidecar for an asset if it exists."""

    from sqlalchemy import select

    result = await db.execute(select(Image).where(Image.id == image_id))
    image = result.scalar_one_or_none()

    if not image:
        raise HTTPException(status_code=404, detail="Image not found")

    sidecar_path = metadata_sidecar_writer.path(image.file_path)
    if not sidecar_path.exists():
        raise HTTPException(status_code=404, detail="Metadata sidecar not found")

    return FileResponse(
        path=str(sidecar_path),
        media_type="application/json",
        filename=sidecar_path.name,
    )


@app.post("/api/rename/auto")
async def auto_rename_images(
    image_ids: List[int],
    db: AsyncSession = Depends(get_db)
):
    """
    Automatically rename images using AI with smart organization.
    Uses AI description, file metadata (date, size), and organizes into folders.
    Optimized with bulk database operations and batch processing.
    """
    from sqlalchemy import select
    from datetime import datetime
    import os

    results = []
    base_dir = Path(settings.upload_dir)

    # Bulk load all images at once (single query instead of N queries)
    result = await db.execute(select(Image).where(Image.id.in_(image_ids)))
    images = result.scalars().all()

    # Create lookup map and track missing images
    image_by_id = {img.id: img for img in images}
    found_image_ids = set(image_by_id.keys())
    missing_image_ids = set(image_ids) - found_image_ids

    for image_id in missing_image_ids:
        results.append({
            "image_id": image_id,
            "success": False,
            "error": "Image not found"
        })

    # Track images that need renaming
    images_to_process = []
    for image_id in found_image_ids:
        image = image_by_id[image_id]
        if not image.ai_description:
            results.append({
                "image_id": image_id,
                "success": False,
                "error": "Image not analyzed yet. Run AI analysis first."
            })
        else:
            images_to_process.append(image)

    # Process all valid images
    file_operations = []  # Track successful file operations for rollback if needed

    for image in images_to_process:
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

            # Store old path for potential rollback
            old_path = file_path

            # Move file
            file_path.rename(new_path)
            file_operations.append((old_path, new_path))

            # Update database record (will be committed in batch)
            image.current_filename = new_filename
            image.file_path = str(new_path)

            # Get relative path for display
            rel_path = new_path.relative_to(base_dir)

            results.append({
                "image_id": image.id,
                "success": True,
                "old_filename": old_path.name,
                "new_filename": new_filename,
                "directory": str(rel_path.parent),
                "quality": quality,
                "description_used": desc_slug
            })

        except Exception as e:
            logger.error(f"Error auto-renaming image {image.id}: {e}")
            results.append({
                "image_id": image.id,
                "success": False,
                "error": str(e)
            })

    # Single commit for all database updates (instead of N commits)
    try:
        await db.commit()
    except Exception as e:
        logger.error(f"Database commit failed during auto-rename: {e}")
        await db.rollback()

        # Attempt to rollback file operations
        for old_path, new_path in reversed(file_operations):
            try:
                if new_path.exists() and not old_path.exists():
                    new_path.rename(old_path)
                    logger.info(f"Rolled back file rename: {new_path} -> {old_path}")
            except Exception as rollback_error:
                logger.error(f"Failed to rollback file operation {new_path}: {rollback_error}")

        raise HTTPException(status_code=500, detail=f"Failed to commit rename operations: {str(e)}")

    return {
        "total": len(image_ids),
        "succeeded": sum(1 for r in results if r.get("success")),
        "results": results
    }


# Project-Aware Rename endpoints (Phase 4)
@app.get("/api/projects/{project_id}/rename/suggestions")
async def get_project_rename_suggestions(
    project_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get portfolio-optimized template suggestions for a project"""
    try:
        rename_service = ProjectRenameService(db)
        suggestions = await rename_service.get_portfolio_suggestions(project_id)
        return suggestions
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error getting rename suggestions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/projects/{project_id}/rename/preview")
async def preview_project_rename(
    project_id: int,
    template: str,
    db: AsyncSession = Depends(get_db)
):
    """Preview project-aware rename for all assets in project"""
    try:
        rename_service = ProjectRenameService(db)
        previews = await rename_service.preview_project_rename(
            project_id=project_id,
            template=template,
        )

        return {
            "project_id": project_id,
            "template": template,
            "total_assets": len(previews),
            "previews": [
                {
                    "image_id": p.image_id,
                    "original_filename": p.original_filename,
                    "proposed_filename": p.proposed_filename,
                    "project_number": p.project_number,
                }
                for p in previews
            ],
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error previewing rename: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/projects/{project_id}/rename/apply")
async def apply_project_rename(
    project_id: int,
    template: str,
    create_backups: bool = True,
    db: AsyncSession = Depends(get_db)
):
    """Apply project-aware rename to all assets in project"""
    try:
        rename_service = ProjectRenameService(db)
        result = await rename_service.apply_project_rename(
            project_id=project_id,
            template=template,
            create_backups=create_backups,
        )

        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error applying rename: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/images/{image_id}/rename/project-aware")
async def rename_image_with_project(
    image_id: int,
    template: Optional[str] = None,
    create_backup: bool = True,
    db: AsyncSession = Depends(get_db)
):
    """Rename a single image using project context"""
    try:
        rename_service = ProjectRenameService(db)
        result = await rename_service.rename_single_with_project(
            image_id=image_id,
            template=template,
            create_backup=create_backup,
        )

        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error renaming image: {e}")
        raise HTTPException(status_code=500, detail=str(e))


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
                "metadata_sidecar_exists": metadata_sidecar_writer.exists(img.file_path),
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


# Project management endpoints
@app.post("/api/projects")
async def create_project(
    request: ProjectCreateRequest,
    db: AsyncSession = Depends(get_db)
):
    """Create a new portfolio project"""
    try:
        project_service = ProjectService(db)
        project = await project_service.create_project(
            name=request.name,
            project_type=request.project_type,
            description=request.description,
            ai_keywords=request.ai_keywords,
            visual_themes=request.visual_themes,
            start_date=request.start_date,
            end_date=request.end_date,
            nextcloud_folder=request.nextcloud_folder,
            default_naming_template=request.default_naming_template,
            portfolio_metadata=request.portfolio_metadata,
            featured_on_portfolio=request.featured_on_portfolio,
        )

        return {
            "id": project.id,
            "name": project.name,
            "slug": project.slug,
            "project_type": project.project_type.value,
            "description": project.description,
            "ai_keywords": project.ai_keywords,
            "visual_themes": project.visual_themes,
            "start_date": project.start_date.isoformat() if project.start_date else None,
            "end_date": project.end_date.isoformat() if project.end_date else None,
            "nextcloud_folder": project.nextcloud_folder,
            "default_naming_template": project.default_naming_template,
            "portfolio_metadata": project.portfolio_metadata,
            "featured_on_portfolio": project.featured_on_portfolio,
            "is_active": project.is_active,
            "created_at": project.created_at.isoformat() if project.created_at else None,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/projects")
async def list_projects(
    project_type: Optional[ProjectType] = None,
    is_active: Optional[bool] = None,
    featured_only: bool = False,
    db: AsyncSession = Depends(get_db)
):
    """List all projects with optional filtering"""
    project_service = ProjectService(db)
    projects = await project_service.list_projects(
        project_type=project_type,
        is_active=is_active,
        featured_only=featured_only,
    )

    return {
        "projects": [
            {
                "id": project.id,
                "name": project.name,
                "slug": project.slug,
                "project_type": project.project_type.value,
                "description": project.description,
                "ai_keywords": project.ai_keywords,
                "visual_themes": project.visual_themes,
                "start_date": project.start_date.isoformat() if project.start_date else None,
                "end_date": project.end_date.isoformat() if project.end_date else None,
                "nextcloud_folder": project.nextcloud_folder,
                "default_naming_template": project.default_naming_template,
                "portfolio_metadata": project.portfolio_metadata,
                "featured_on_portfolio": project.featured_on_portfolio,
                "is_active": project.is_active,
                "asset_count": len(project.images),
                "created_at": project.created_at.isoformat() if project.created_at else None,
            }
            for project in projects
        ]
    }


@app.get("/api/projects/{project_id}")
async def get_project(
    project_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get a specific project with all details"""
    project_service = ProjectService(db)
    project = await project_service.get_project(project_id)

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    return {
        "id": project.id,
        "name": project.name,
        "slug": project.slug,
        "project_type": project.project_type.value,
        "description": project.description,
        "ai_keywords": project.ai_keywords,
        "visual_themes": project.visual_themes,
        "start_date": project.start_date.isoformat() if project.start_date else None,
        "end_date": project.end_date.isoformat() if project.end_date else None,
        "nextcloud_folder": project.nextcloud_folder,
        "default_naming_template": project.default_naming_template,
        "portfolio_metadata": project.portfolio_metadata,
        "featured_on_portfolio": project.featured_on_portfolio,
        "is_active": project.is_active,
        "created_at": project.created_at.isoformat() if project.created_at else None,
        "images": [
            {
                "id": img.id,
                "current_filename": img.current_filename,
                "file_path": img.file_path,
                "media_type": img.media_type.value,
                "ai_description": img.ai_description,
                "ai_tags": img.ai_tags,
            }
            for img in project.images
        ],
    }


@app.get("/api/projects/slug/{slug}")
async def get_project_by_slug(
    slug: str,
    db: AsyncSession = Depends(get_db)
):
    """Get a project by its slug"""
    project_service = ProjectService(db)
    project = await project_service.get_project_by_slug(slug)

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    return {
        "id": project.id,
        "name": project.name,
        "slug": project.slug,
        "project_type": project.project_type.value,
        "description": project.description,
        "ai_keywords": project.ai_keywords,
        "visual_themes": project.visual_themes,
        "start_date": project.start_date.isoformat() if project.start_date else None,
        "end_date": project.end_date.isoformat() if project.end_date else None,
        "nextcloud_folder": project.nextcloud_folder,
        "default_naming_template": project.default_naming_template,
        "portfolio_metadata": project.portfolio_metadata,
        "featured_on_portfolio": project.featured_on_portfolio,
        "is_active": project.is_active,
        "created_at": project.created_at.isoformat() if project.created_at else None,
    }


@app.patch("/api/projects/{project_id}")
async def update_project(
    project_id: int,
    request: ProjectUpdateRequest,
    db: AsyncSession = Depends(get_db)
):
    """Update a project"""
    try:
        project_service = ProjectService(db)

        # Only include fields that were provided
        updates = {k: v for k, v in request.dict().items() if v is not None}

        project = await project_service.update_project(project_id, **updates)

        return {
            "id": project.id,
            "name": project.name,
            "slug": project.slug,
            "project_type": project.project_type.value,
            "description": project.description,
            "ai_keywords": project.ai_keywords,
            "visual_themes": project.visual_themes,
            "start_date": project.start_date.isoformat() if project.start_date else None,
            "end_date": project.end_date.isoformat() if project.end_date else None,
            "nextcloud_folder": project.nextcloud_folder,
            "default_naming_template": project.default_naming_template,
            "portfolio_metadata": project.portfolio_metadata,
            "featured_on_portfolio": project.featured_on_portfolio,
            "is_active": project.is_active,
            "updated_at": project.updated_at.isoformat() if project.updated_at else None,
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.delete("/api/projects/{project_id}")
async def delete_project(
    project_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Delete (archive) a project"""
    project_service = ProjectService(db)
    success = await project_service.delete_project(project_id)

    if not success:
        raise HTTPException(status_code=404, detail="Project not found")

    return {"success": True}


@app.post("/api/projects/{project_id}/assign-assets")
async def assign_assets_to_project(
    project_id: int,
    request: ProjectAssignImagesRequest,
    db: AsyncSession = Depends(get_db)
):
    """Assign assets to a project (with automatic Nextcloud sync)"""
    try:
        # Create sync service
        sync_service = NextcloudSyncService(db, nextcloud_client)

        # Create project service with sync
        project_service = ProjectService(db, sync_service=sync_service)
        project = await project_service.assign_images_to_project(
            project_id,
            request.image_ids,
            replace=request.replace,
        )

        return {
            "success": True,
            "project_id": project.id,
            "project_name": project.name,
            "assigned_count": len(project.images),
            "auto_sync_enabled": settings.nextcloud_auto_sync,
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.delete("/api/projects/{project_id}/remove-assets")
async def remove_assets_from_project(
    project_id: int,
    request: ProjectAssignImagesRequest,
    db: AsyncSession = Depends(get_db)
):
    """Remove assets from a project"""
    try:
        project_service = ProjectService(db)
        project = await project_service.remove_images_from_project(
            project_id,
            request.image_ids,
        )

        return {
            "success": True,
            "project_id": project.id,
            "project_name": project.name,
            "remaining_count": len(project.images),
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.get("/api/projects/unassigned/images")
async def get_unassigned_images(db: AsyncSession = Depends(get_db)):
    """Get all images not assigned to any project"""
    project_service = ProjectService(db)
    images = await project_service.get_unassigned_images()

    return {
        "count": len(images),
        "images": [
            {
                "id": img.id,
                "current_filename": img.current_filename,
                "file_path": img.file_path,
                "media_type": img.media_type.value,
                "ai_description": img.ai_description,
                "ai_tags": img.ai_tags,
                "created_at": img.created_at.isoformat() if img.created_at else None,
            }
            for img in images
        ],
    }


@app.get("/api/projects/{project_id}/stats")
async def get_project_stats(
    project_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get statistics for a project"""
    try:
        project_service = ProjectService(db)
        stats = await project_service.get_project_stats(project_id)
        return stats
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# AI Project Classification endpoints
@app.post("/api/projects/classify/{image_id}")
async def classify_image_project(
    image_id: int,
    auto_assign: bool = True,
    db: AsyncSession = Depends(get_db)
):
    """
    Classify an image and suggest/assign project

    Args:
        image_id: Image ID to classify
        auto_assign: Whether to automatically assign to best matching project
    """
    try:
        # Get image
        result = await db.execute(select(Image).where(Image.id == image_id))
        image = result.scalar_one_or_none()

        if not image:
            raise HTTPException(status_code=404, detail="Image not found")

        # Run classification
        classifier = ProjectClassifier(db, llava_client)
        classification = await classifier.classify_image(
            image=image,
            auto_assign=auto_assign,
        )

        return {
            "image_id": classification.image_id,
            "assigned_project_id": classification.assigned_project_id,
            "assigned_project_name": classification.assigned_project_name,
            "confidence": classification.confidence,
            "requires_review": classification.requires_review,
            "reasons": classification.reasons,
            "all_matches": [
                {
                    "project_id": match.project_id,
                    "project_name": match.project_name,
                    "confidence": match.confidence,
                    "reasons": match.reasons,
                    "keyword_matches": match.keyword_matches,
                    "theme_matches": match.theme_matches,
                }
                for match in classification.all_matches
            ],
        }
    except Exception as e:
        logger.error(f"Error classifying image {image_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/projects/classify-batch")
async def classify_batch_projects(
    image_ids: List[int],
    auto_assign: bool = True,
    db: AsyncSession = Depends(get_db)
):
    """
    Classify multiple images in batch

    Args:
        image_ids: List of image IDs to classify
        auto_assign: Whether to automatically assign to projects
    """
    try:
        classifier = ProjectClassifier(db, llava_client)
        classifications = await classifier.classify_batch(
            image_ids=image_ids,
            auto_assign=auto_assign,
        )

        return {
            "total": len(image_ids),
            "classifications": [
                {
                    "image_id": c.image_id,
                    "assigned_project_id": c.assigned_project_id,
                    "assigned_project_name": c.assigned_project_name,
                    "confidence": c.confidence,
                    "requires_review": c.requires_review,
                    "reasons": c.reasons,
                }
                for c in classifications
            ],
        }
    except Exception as e:
        logger.error(f"Error classifying batch: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/projects/suggestions/{image_id}")
async def get_project_suggestions(
    image_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get project suggestions for an image without assigning"""
    try:
        classifier = ProjectClassifier(db, llava_client)
        suggestions = await classifier.suggest_project(image_id)

        return {
            "image_id": image_id,
            "suggestions": [
                {
                    "project_id": match.project_id,
                    "project_name": match.project_name,
                    "project_slug": match.project_slug,
                    "confidence": match.confidence,
                    "reasons": match.reasons,
                    "keyword_matches": match.keyword_matches,
                    "theme_matches": match.theme_matches,
                }
                for match in suggestions
            ],
        }
    except Exception as e:
        logger.error(f"Error getting suggestions for image {image_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/projects/review-queue")
async def get_review_queue(db: AsyncSession = Depends(get_db)):
    """Get images that need manual project assignment review"""
    try:
        classifier = ProjectClassifier(db, llava_client)
        images = await classifier.get_review_queue()

        return {
            "count": len(images),
            "images": [
                {
                    "id": img.id,
                    "current_filename": img.current_filename,
                    "file_path": img.file_path,
                    "media_type": img.media_type.value,
                    "ai_description": img.ai_description,
                    "ai_tags": img.ai_tags,
                    "ai_scene": img.ai_scene,
                    "created_at": img.created_at.isoformat() if img.created_at else None,
                }
                for img in images
            ],
        }
    except Exception as e:
        logger.error(f"Error getting review queue: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class ProjectLearningRequest(BaseModel):
    image_id: int
    project_id: int
    is_correct: bool = True


@app.post("/api/projects/learn")
async def learn_from_assignment(
    request: ProjectLearningRequest,
    db: AsyncSession = Depends(get_db)
):
    """Learn from manual project assignments to improve AI"""
    try:
        classifier = ProjectClassifier(db, llava_client)
        await classifier.learn_from_assignment(
            image_id=request.image_id,
            project_id=request.project_id,
            is_correct=request.is_correct,
        )

        return {"success": True, "message": "Learning complete"}
    except Exception as e:
        logger.error(f"Error learning from assignment: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Nextcloud Sync endpoints
@app.post("/api/nextcloud/sync/project/{project_id}")
async def sync_project_to_nextcloud(
    project_id: int,
    force: bool = False,
    db: AsyncSession = Depends(get_db)
):
    """
    Sync all assets in a project to Nextcloud

    Args:
        project_id: Project ID
        force: Force re-sync of already synced assets
    """
    try:
        sync_service = NextcloudSyncService(db, nextcloud_client)
        result = await sync_service.sync_project(project_id, force=force)

        return {
            "success": True,
            "project_id": result.project_id,
            "project_name": result.project_name,
            "total_assets": result.total_assets,
            "synced": result.synced,
            "failed": result.failed,
            "skipped": result.skipped,
            "results": [
                {
                    "image_id": r.image_id,
                    "success": r.success,
                    "nextcloud_path": r.nextcloud_path,
                    "error": r.error,
                }
                for r in result.results
            ],
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error syncing project {project_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/nextcloud/sync/batch")
async def sync_batch_to_nextcloud(
    image_ids: List[int],
    force: bool = False,
    db: AsyncSession = Depends(get_db)
):
    """
    Sync multiple assets to Nextcloud

    Args:
        image_ids: List of image IDs to sync
        force: Force re-sync of already synced assets
    """
    try:
        sync_service = NextcloudSyncService(db, nextcloud_client)
        results = await sync_service.sync_batch(image_ids, force=force)

        succeeded = sum(1 for r in results if r.success)
        failed = sum(1 for r in results if not r.success)

        return {
            "success": True,
            "total": len(image_ids),
            "synced": succeeded,
            "failed": failed,
            "results": [
                {
                    "image_id": r.image_id,
                    "success": r.success,
                    "nextcloud_path": r.nextcloud_path,
                    "error": r.error,
                }
                for r in results
            ],
        }
    except Exception as e:
        logger.error(f"Error syncing batch: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/nextcloud/sync/status/{project_id}")
async def get_sync_status(
    project_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get Nextcloud sync status for a project"""
    try:
        sync_service = NextcloudSyncService(db, nextcloud_client)
        status = await sync_service.get_sync_status(project_id)
        return status
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error getting sync status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/nextcloud/validate")
async def validate_nextcloud_connection(db: AsyncSession = Depends(get_db)):
    """Test Nextcloud connection"""
    try:
        sync_service = NextcloudSyncService(db, nextcloud_client)
        result = await sync_service.validate_nextcloud_connection()
        return result
    except Exception as e:
        logger.error(f"Error validating Nextcloud connection: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/nextcloud/import/{project_id}")
async def import_from_nextcloud(
    project_id: int,
    remote_folder: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Import files from Nextcloud into a project

    Args:
        project_id: Project to import into
        remote_folder: Remote folder to import from (uses project folder if None)
    """
    try:
        sync_service = NextcloudSyncService(db, nextcloud_client)
        result = await sync_service.import_from_nextcloud(
            project_id=project_id,
            remote_folder=remote_folder,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error importing from Nextcloud: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Feedback and Error Logging endpoints
@app.post("/api/feedback")
async def submit_feedback(
    request: FeedbackRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Submit user feedback or bug reports

    Args:
        request: Feedback data including type, title, description, etc.

    Returns:
        Success response with ticket ID
    """
    try:
        # Generate a unique ticket ID
        ticket_id = str(uuid4())[:8].upper()

        # Log the feedback
        feedback_type = request.type.upper()
        logger.info(
            f"[FEEDBACK-{ticket_id}] Type: {feedback_type} | "
            f"Title: {request.title} | "
            f"Email: {request.email or 'anonymous'}"
        )
        logger.info(f"[FEEDBACK-{ticket_id}] Description: {request.description}")

        if request.stepsToReproduce:
            logger.info(f"[FEEDBACK-{ticket_id}] Steps to reproduce:\n{request.stepsToReproduce}")

        if request.systemInfo:
            logger.info(f"[FEEDBACK-{ticket_id}] System info: {request.systemInfo}")

        # TODO: In production, this would:
        # - Store feedback in database
        # - Send email notification
        # - Create issue in issue tracker (e.g., GitHub, Jira)
        # - Trigger webhooks/integrations

        return {
            "success": True,
            "message": "Thank you for your feedback!",
            "ticketId": ticket_id
        }

    except Exception as e:
        logger.error(f"Error submitting feedback: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to submit feedback. Please try again later."
        )


@app.post("/api/errors/log")
async def log_error(request: ErrorLogRequest):
    """
    Log errors from the frontend for monitoring and debugging

    Args:
        request: Error details including title, message, category, severity, etc.

    Returns:
        Success response
    """
    try:
        # Log the error with appropriate severity
        error_id = str(uuid4())[:8].upper()
        log_message = (
            f"[CLIENT-ERROR-{error_id}] {request.title}: {request.message} | "
            f"Category: {request.category} | Severity: {request.severity}"
        )

        if request.severity == "critical":
            logger.critical(log_message)
        elif request.severity == "error":
            logger.error(log_message)
        elif request.severity == "warning":
            logger.warning(log_message)
        else:
            logger.info(log_message)

        if request.technicalDetails:
            logger.error(f"[CLIENT-ERROR-{error_id}] Technical details: {request.technicalDetails}")

        if request.context:
            logger.error(f"[CLIENT-ERROR-{error_id}] Context: {request.context}")

        if request.userAgent:
            logger.info(f"[CLIENT-ERROR-{error_id}] User Agent: {request.userAgent}")

        if request.url:
            logger.info(f"[CLIENT-ERROR-{error_id}] URL: {request.url}")

        # TODO: In production, this would:
        # - Store error in database for analytics
        # - Send to error tracking service (e.g., Sentry, Rollbar)
        # - Trigger alerts for critical errors
        # - Aggregate errors for monitoring dashboard

        return {
            "success": True,
            "errorId": error_id
        }

    except Exception as e:
        logger.error(f"Error logging client error: {e}")
        # Don't raise exception - we don't want error logging to cause more errors
        return {
            "success": False,
            "message": "Failed to log error"
        }


# Serve frontend static files and handle SPA routing
static_dir = Path(__file__).parent / "static"
if static_dir.exists():
    # Mount static files for /assets and other static resources
    app.mount("/assets", StaticFiles(directory=str(static_dir / "assets")), name="assets")

    # Catch-all route for SPA - must be last
    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        """Serve index.html for all non-API routes to support SPA routing"""
        # Serve static files if they exist
        file_path = static_dir / full_path
        if file_path.is_file():
            return FileResponse(file_path)
        # Otherwise serve index.html for React Router
        return FileResponse(static_dir / "index.html")


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug
    )
