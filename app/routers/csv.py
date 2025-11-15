"""
API endpoints for CSV import (JSPOW v2)
"""
import logging
import os
import shutil
from typing import List, Optional
from uuid import UUID
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, BackgroundTasks
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.database import get_db
from app.models import (
    CSVImport,
    CSVImportRow,
    CSVImportStatus,
    CSVImportRowStatus,
    Image,
)
from app.services.csv_service import CSVImportService
from app.config import settings
from app.routers.websocket import manager as ws_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v2/csv", tags=["CSV Import v2"])


# ============================================================================
# Request/Response Models
# ============================================================================

class CSVImportResponse(BaseModel):
    id: str
    filename: str
    status: str
    total_rows: int
    processed_rows: int
    matched_rows: int
    failed_rows: int
    error_message: Optional[str] = None
    created_at: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None


class CSVImportRowResponse(BaseModel):
    id: str
    row_number: int
    status: str
    priority: Optional[str] = None
    category: Optional[str] = None
    page_component: Optional[str] = None
    asset_name: Optional[str] = None
    file_path: Optional[str] = None
    dimensions: Optional[str] = None
    format: Optional[str] = None
    file_size_target: Optional[str] = None
    csv_status: Optional[str] = None
    notes: Optional[str] = None
    matched_asset_id: Optional[int] = None
    match_score: Optional[float] = None
    error_message: Optional[str] = None


class CSVImportDetailResponse(BaseModel):
    import_info: CSVImportResponse
    rows: List[CSVImportRowResponse]
    matched_assets: Optional[List[dict]] = None


class CSVImportStatsResponse(BaseModel):
    total_imports: int
    pending_imports: int
    processing_imports: int
    completed_imports: int
    failed_imports: int


# ============================================================================
# Helper Functions
# ============================================================================

def csv_import_to_response(csv_import: CSVImport) -> CSVImportResponse:
    """Convert CSVImport model to response"""
    return CSVImportResponse(
        id=str(csv_import.id),
        filename=csv_import.filename,
        status=csv_import.status.value,
        total_rows=csv_import.total_rows,
        processed_rows=csv_import.processed_rows,
        matched_rows=csv_import.matched_rows,
        failed_rows=csv_import.failed_rows,
        error_message=csv_import.error_message,
        created_at=csv_import.created_at.isoformat() if csv_import.created_at else "",
        started_at=csv_import.started_at.isoformat() if csv_import.started_at else None,
        completed_at=csv_import.completed_at.isoformat() if csv_import.completed_at else None,
    )


def csv_import_row_to_response(row: CSVImportRow) -> CSVImportRowResponse:
    """Convert CSVImportRow model to response"""
    return CSVImportRowResponse(
        id=str(row.id),
        row_number=row.row_number,
        status=row.status.value,
        priority=row.priority,
        category=row.category,
        page_component=row.page_component,
        asset_name=row.asset_name,
        file_path=row.file_path,
        dimensions=row.dimensions,
        format=row.format,
        file_size_target=row.file_size_target,
        csv_status=row.csv_status,
        notes=row.notes,
        matched_asset_id=row.matched_asset_id,
        match_score=row.match_score,
        error_message=row.error_message,
    )


async def process_csv_import_background(csv_import_id: UUID, db: AsyncSession):
    """Background task to process CSV import"""
    try:
        service = CSVImportService(db)
        csv_import = await service.process_import_job(csv_import_id)

        # Broadcast completion via WebSocket
        await ws_manager.broadcast({
            "type": "csv_import_completed",
            "import_id": str(csv_import_id),
            "status": csv_import.status.value,
            "matched_rows": csv_import.matched_rows,
            "failed_rows": csv_import.failed_rows,
        })

    except Exception as e:
        logger.error(f"Error processing CSV import {csv_import_id}: {e}")


# ============================================================================
# CSV Import Endpoints
# ============================================================================

@router.post("/import", response_model=CSVImportResponse, status_code=status.HTTP_201_CREATED)
async def upload_csv(
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Upload CSV file and start import process

    Expected CSV columns:
    - Priority
    - Category
    - Page_Component
    - Asset_Name (required)
    - File_Path (required)
    - Dimensions
    - Format
    - File_Size_Target
    - Status
    - Notes
    """
    # Validate file type
    if not file.filename.endswith('.csv'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be a CSV file"
        )

    # Create temp directory if it doesn't exist
    temp_dir = os.path.join(settings.upload_dir, "csv_imports")
    os.makedirs(temp_dir, exist_ok=True)

    # Save uploaded file
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    safe_filename = f"{timestamp}_{file.filename}"
    file_path = os.path.join(temp_dir, safe_filename)

    try:
        with open(file_path, "wb") as f:
            shutil.copyfileobj(file.file, f)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save file: {str(e)}"
        )
    finally:
        await file.close()

    # Parse CSV
    service = CSVImportService(db)
    rows, error = await service.parse_csv_file(file_path)

    if error:
        # Clean up file
        if os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error
        )

    # Create import job
    csv_import = await service.create_import_job(
        filename=file.filename,
        file_path=file_path,
        total_rows=len(rows),
        metadata={"uploaded_at": datetime.utcnow().isoformat()}
    )

    # Create import rows
    await service.create_import_rows(csv_import.id, rows)

    # Start background processing
    if background_tasks:
        background_tasks.add_task(process_csv_import_background, csv_import.id, db)
    else:
        # Process synchronously if no background tasks available
        await service.process_import_job(csv_import.id)
        await db.refresh(csv_import)

    # Broadcast import started
    await ws_manager.broadcast({
        "type": "csv_import_started",
        "import_id": str(csv_import.id),
        "filename": csv_import.filename,
        "total_rows": csv_import.total_rows,
    })

    return csv_import_to_response(csv_import)


@router.get("", response_model=List[CSVImportResponse])
async def list_csv_imports(
    status_filter: Optional[CSVImportStatus] = None,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db)
):
    """
    List CSV import jobs
    """
    query = select(CSVImport).order_by(CSVImport.created_at.desc())

    if status_filter:
        query = query.where(CSVImport.status == status_filter)

    query = query.limit(limit).offset(offset)

    result = await db.execute(query)
    imports = result.scalars().all()

    return [csv_import_to_response(imp) for imp in imports]


@router.get("/stats", response_model=CSVImportStatsResponse)
async def get_csv_import_stats(db: AsyncSession = Depends(get_db)):
    """
    Get CSV import statistics
    """
    result = await db.execute(select(CSVImport))
    imports = result.scalars().all()

    stats = {
        "total_imports": len(imports),
        "pending_imports": sum(1 for i in imports if i.status == CSVImportStatus.PENDING),
        "processing_imports": sum(1 for i in imports if i.status == CSVImportStatus.PROCESSING),
        "completed_imports": sum(1 for i in imports if i.status == CSVImportStatus.COMPLETED),
        "failed_imports": sum(1 for i in imports if i.status == CSVImportStatus.FAILED),
    }

    return CSVImportStatsResponse(**stats)


@router.get("/{import_id}", response_model=CSVImportDetailResponse)
async def get_csv_import_detail(
    import_id: UUID,
    include_assets: bool = False,
    db: AsyncSession = Depends(get_db)
):
    """
    Get detailed information about a CSV import
    """
    # Get import job
    result = await db.execute(
        select(CSVImport).where(CSVImport.id == import_id)
    )
    csv_import = result.scalar_one_or_none()

    if not csv_import:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"CSV import {import_id} not found"
        )

    # Get import rows
    result = await db.execute(
        select(CSVImportRow)
        .where(CSVImportRow.csv_import_id == import_id)
        .order_by(CSVImportRow.row_number)
    )
    rows = result.scalars().all()

    # Optionally include matched asset details
    matched_assets = None
    if include_assets:
        matched_asset_ids = [r.matched_asset_id for r in rows if r.matched_asset_id]
        if matched_asset_ids:
            result = await db.execute(
                select(Image).where(Image.id.in_(matched_asset_ids))
            )
            assets = result.scalars().all()
            matched_assets = [
                {
                    "id": asset.id,
                    "filename": asset.current_filename,
                    "file_path": asset.file_path,
                    "width": asset.width,
                    "height": asset.height,
                }
                for asset in assets
            ]

    return CSVImportDetailResponse(
        import_info=csv_import_to_response(csv_import),
        rows=[csv_import_row_to_response(row) for row in rows],
        matched_assets=matched_assets,
    )


@router.get("/{import_id}/rows", response_model=List[CSVImportRowResponse])
async def get_csv_import_rows(
    import_id: UUID,
    status_filter: Optional[CSVImportRowStatus] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Get rows for a specific CSV import
    """
    service = CSVImportService(db)
    rows = await service.get_import_rows(import_id, status_filter)

    return [csv_import_row_to_response(row) for row in rows]


@router.delete("/{import_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_csv_import(
    import_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Delete a CSV import job and its rows
    """
    result = await db.execute(
        select(CSVImport).where(CSVImport.id == import_id)
    )
    csv_import = result.scalar_one_or_none()

    if not csv_import:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"CSV import {import_id} not found"
        )

    # Delete file if it exists
    if csv_import.file_path and os.path.exists(csv_import.file_path):
        try:
            os.remove(csv_import.file_path)
        except Exception as e:
            logger.warning(f"Failed to delete CSV file {csv_import.file_path}: {e}")

    # Delete database record (cascade will delete rows)
    await db.delete(csv_import)
    await db.commit()

    return None
