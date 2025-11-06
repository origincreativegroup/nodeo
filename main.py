"""
jspow - AI-powered image file renaming and organization tool
Main FastAPI application
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI, File, UploadFile, Depends, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from pathlib import Path
from typing import List, Optional
import logging
import uvicorn
from datetime import datetime
from uuid import uuid4

from app.config import settings
from app.database import init_db, close_db, get_db
from app.models import Image, RenameJob, Template, ProcessingQueue, ProcessStatus, StorageType
from app.ai import llava_client
from app.services import RenameEngine, TemplateParser, PREDEFINED_TEMPLATES
from app.storage import nextcloud_client, r2_client, stream_client, storage_manager

# Configure logging
logging.basicConfig(
    level=logging.INFO if settings.debug else logging.WARNING,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


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

    for file in files:
        try:
            # Validate file extension
            ext = Path(file.filename).suffix.lower().lstrip('.')
            if ext not in settings.allowed_image_exts:
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
            from PIL import Image as PILImage
            with PILImage.open(working_path) as img:
                width, height = img.size

            image_record = Image(
                original_filename=file.filename,
                current_filename=file.filename,
                file_path=str(working_path),
                file_size=len(content),
                mime_type=file.content_type,
                width=width,
                height=height,
                storage_type=StorageType.LOCAL
            )

            db.add(image_record)
            await db.commit()
            await db.refresh(image_record)

            results.append({
                "filename": file.filename,
                "success": True,
                "id": image_record.id,
                "size": len(content),
                "dimensions": f"{width}x{height}"
            })

        except Exception as e:
            logger.error(f"Error uploading {file.filename}: {e}")
            results.append({
                "filename": file.filename,
                "success": False,
                "error": str(e)
            })

    return {
        "total": len(files),
        "succeeded": sum(1 for r in results if r.get("success")),
        "results": results
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


# Pydantic models for request bodies
from pydantic import BaseModel

class RenamePreviewRequest(BaseModel):
    template: str
    image_ids: List[int]

class RenameApplyRequest(BaseModel):
    template: str
    image_ids: List[int]
    create_backups: bool = True

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
            'height': image.height
        }

        ext = Path(image.current_filename).suffix
        new_filename = engine.generate_filename(metadata, index=idx, original_extension=ext)

        previews.append({
            'image_id': image_id,
            'current_filename': image.current_filename,
            'proposed_filename': new_filename
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
                'height': image.height
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

    result = await db.execute(select(Image).order_by(Image.created_at.desc()))
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
                "width": img.width,
                "height": img.height,
                "ai_description": img.ai_description,
                "ai_tags": img.ai_tags,
                "ai_objects": img.ai_objects,
                "ai_scene": img.ai_scene,
                "analyzed_at": img.analyzed_at.isoformat() if img.analyzed_at else None,
                "created_at": img.created_at.isoformat() if img.created_at else None,
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
