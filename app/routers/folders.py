"""
API endpoints for watched folder management (JSPOW v2)
"""
import logging
from typing import List, Optional
from uuid import UUID
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.database import get_db
from app.models import (
    WatchedFolder,
    WatchedFolderStatus,
    RenameSuggestion,
    SuggestionStatus,
    ActivityLog,
    ActivityActionType
)
from app.services.folder_watcher import watcher_manager
from app.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v2/folders", tags=["Folders v2"])


# ============================================================================
# Request/Response Models
# ============================================================================

class WatchedFolderCreate(BaseModel):
    path: str
    name: Optional[str] = None


class WatchedFolderUpdate(BaseModel):
    name: Optional[str] = None
    status: Optional[WatchedFolderStatus] = None


class WatchedFolderResponse(BaseModel):
    id: str
    path: str
    name: str
    status: str
    file_count: int
    analyzed_count: int
    pending_count: int
    last_scan_at: Optional[str] = None
    error_message: Optional[str] = None
    created_at: str
    updated_at: Optional[str] = None


class FolderStatsResponse(BaseModel):
    total_folders: int
    active_folders: int
    paused_folders: int
    error_folders: int
    scanning_folders: int
    total_files: int
    total_analyzed: int
    total_pending: int


# ============================================================================
# Folder Management Endpoints
# ============================================================================

@router.post("", response_model=WatchedFolderResponse, status_code=status.HTTP_201_CREATED)
async def add_watched_folder(
    request: WatchedFolderCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Add a new folder to watch for automatic file processing
    """
    # Validate path exists
    folder_path = Path(request.path)
    if not folder_path.exists():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Folder does not exist: {request.path}"
        )

    if not folder_path.is_dir():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Path is not a directory: {request.path}"
        )

    # Check if folder is already being watched
    result = await db.execute(
        select(WatchedFolder).where(WatchedFolder.path == str(folder_path.resolve()))
    )
    existing = result.scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Folder is already being watched"
        )

    # Check max folders limit
    count_result = await db.execute(
        select(func.count(WatchedFolder.id)).where(
            WatchedFolder.status.in_([
                WatchedFolderStatus.ACTIVE,
                WatchedFolderStatus.SCANNING
            ])
        )
    )
    active_count = count_result.scalar()
    if active_count >= settings.watcher_max_folders:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Maximum number of watched folders ({settings.watcher_max_folders}) reached"
        )

    # Create watched folder
    folder_name = request.name or folder_path.name
    watched_folder = WatchedFolder(
        path=str(folder_path.resolve()),
        name=folder_name,
        status=WatchedFolderStatus.ACTIVE,
        file_count=0,
        analyzed_count=0,
        pending_count=0
    )

    db.add(watched_folder)
    await db.commit()
    await db.refresh(watched_folder)

    # Create activity log entry
    activity_log = ActivityLog(
        watched_folder_id=watched_folder.id,
        action_type=ActivityActionType.FOLDER_ADDED,
        folder_path=watched_folder.path,
        status="success",
        metadata={"name": watched_folder.name}
    )
    db.add(activity_log)
    await db.commit()

    # Start watcher
    await watcher_manager.add_watcher(watched_folder.id, watched_folder.path)

    # Trigger initial scan
    await watcher_manager.scan_folder(watched_folder.id)

    return WatchedFolderResponse(
        id=str(watched_folder.id),
        path=watched_folder.path,
        name=watched_folder.name,
        status=watched_folder.status.value,
        file_count=watched_folder.file_count,
        analyzed_count=watched_folder.analyzed_count,
        pending_count=watched_folder.pending_count,
        last_scan_at=watched_folder.last_scan_at.isoformat() if watched_folder.last_scan_at else None,
        error_message=watched_folder.error_message,
        created_at=watched_folder.created_at.isoformat(),
        updated_at=watched_folder.updated_at.isoformat() if watched_folder.updated_at else None
    )


@router.get("", response_model=List[WatchedFolderResponse])
async def list_watched_folders(
    status_filter: Optional[WatchedFolderStatus] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    List all watched folders with stats
    """
    query = select(WatchedFolder).order_by(WatchedFolder.created_at.desc())

    if status_filter:
        query = query.where(WatchedFolder.status == status_filter)

    result = await db.execute(query)
    folders = result.scalars().all()

    return [
        WatchedFolderResponse(
            id=str(folder.id),
            path=folder.path,
            name=folder.name,
            status=folder.status.value,
            file_count=folder.file_count,
            analyzed_count=folder.analyzed_count,
            pending_count=folder.pending_count,
            last_scan_at=folder.last_scan_at.isoformat() if folder.last_scan_at else None,
            error_message=folder.error_message,
            created_at=folder.created_at.isoformat(),
            updated_at=folder.updated_at.isoformat() if folder.updated_at else None
        )
        for folder in folders
    ]


@router.get("/stats", response_model=FolderStatsResponse)
async def get_folder_stats(db: AsyncSession = Depends(get_db)):
    """
    Get aggregate statistics for all watched folders
    """
    # Get counts by status
    status_counts = await db.execute(
        select(
            WatchedFolder.status,
            func.count(WatchedFolder.id)
        ).group_by(WatchedFolder.status)
    )
    status_map = {status: count for status, count in status_counts}

    # Get totals
    totals = await db.execute(
        select(
            func.count(WatchedFolder.id).label('total'),
            func.sum(WatchedFolder.file_count).label('files'),
            func.sum(WatchedFolder.analyzed_count).label('analyzed'),
            func.sum(WatchedFolder.pending_count).label('pending')
        )
    )
    totals_row = totals.one()

    return FolderStatsResponse(
        total_folders=totals_row.total or 0,
        active_folders=status_map.get(WatchedFolderStatus.ACTIVE, 0),
        paused_folders=status_map.get(WatchedFolderStatus.PAUSED, 0),
        error_folders=status_map.get(WatchedFolderStatus.ERROR, 0),
        scanning_folders=status_map.get(WatchedFolderStatus.SCANNING, 0),
        total_files=totals_row.files or 0,
        total_analyzed=totals_row.analyzed or 0,
        total_pending=totals_row.pending or 0
    )


@router.get("/{folder_id}", response_model=WatchedFolderResponse)
async def get_watched_folder(
    folder_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Get details of a specific watched folder
    """
    result = await db.execute(
        select(WatchedFolder).where(WatchedFolder.id == folder_id)
    )
    folder = result.scalar_one_or_none()

    if not folder:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Watched folder not found"
        )

    return WatchedFolderResponse(
        id=str(folder.id),
        path=folder.path,
        name=folder.name,
        status=folder.status.value,
        file_count=folder.file_count,
        analyzed_count=folder.analyzed_count,
        pending_count=folder.pending_count,
        last_scan_at=folder.last_scan_at.isoformat() if folder.last_scan_at else None,
        error_message=folder.error_message,
        created_at=folder.created_at.isoformat(),
        updated_at=folder.updated_at.isoformat() if folder.updated_at else None
    )


@router.patch("/{folder_id}", response_model=WatchedFolderResponse)
async def update_watched_folder(
    folder_id: UUID,
    request: WatchedFolderUpdate,
    db: AsyncSession = Depends(get_db)
):
    """
    Update watched folder settings (name, status)
    """
    result = await db.execute(
        select(WatchedFolder).where(WatchedFolder.id == folder_id)
    )
    folder = result.scalar_one_or_none()

    if not folder:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Watched folder not found"
        )

    # Update name if provided
    if request.name is not None:
        folder.name = request.name

    # Update status if provided
    if request.status is not None:
        old_status = folder.status
        folder.status = request.status

        # Handle watcher based on status change
        if old_status != request.status:
            if request.status == WatchedFolderStatus.PAUSED:
                await watcher_manager.pause_watcher(folder_id)
            elif request.status == WatchedFolderStatus.ACTIVE and old_status == WatchedFolderStatus.PAUSED:
                await watcher_manager.resume_watcher(folder_id)

    await db.commit()
    await db.refresh(folder)

    return WatchedFolderResponse(
        id=str(folder.id),
        path=folder.path,
        name=folder.name,
        status=folder.status.value,
        file_count=folder.file_count,
        analyzed_count=folder.analyzed_count,
        pending_count=folder.pending_count,
        last_scan_at=folder.last_scan_at.isoformat() if folder.last_scan_at else None,
        error_message=folder.error_message,
        created_at=folder.created_at.isoformat(),
        updated_at=folder.updated_at.isoformat() if folder.updated_at else None
    )


@router.delete("/{folder_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_watched_folder(
    folder_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Remove a watched folder (stops watching and deletes configuration)
    """
    result = await db.execute(
        select(WatchedFolder).where(WatchedFolder.id == folder_id)
    )
    folder = result.scalar_one_or_none()

    if not folder:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Watched folder not found"
        )

    # Stop watcher
    await watcher_manager.remove_watcher(folder_id)

    # Create activity log entry
    activity_log = ActivityLog(
        watched_folder_id=folder.id,
        action_type=ActivityActionType.FOLDER_REMOVED,
        folder_path=folder.path,
        status="success",
        metadata={"name": folder.name}
    )
    db.add(activity_log)

    # Delete folder (cascades to suggestions and activity logs)
    await db.delete(folder)
    await db.commit()

    return None


@router.post("/{folder_id}/rescan", status_code=status.HTTP_202_ACCEPTED)
async def rescan_folder(
    folder_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Trigger manual rescan of a watched folder
    """
    result = await db.execute(
        select(WatchedFolder).where(WatchedFolder.id == folder_id)
    )
    folder = result.scalar_one_or_none()

    if not folder:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Watched folder not found"
        )

    if folder.status == WatchedFolderStatus.SCANNING:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Folder is already being scanned"
        )

    # Trigger scan
    await watcher_manager.scan_folder(folder_id)

    return {
        "message": "Scan initiated",
        "folder_id": str(folder_id)
    }


@router.get("/{folder_id}/progress")
async def get_folder_progress(
    folder_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Get real-time progress for a folder scan
    """
    result = await db.execute(
        select(WatchedFolder).where(WatchedFolder.id == folder_id)
    )
    folder = result.scalar_one_or_none()

    if not folder:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Watched folder not found"
        )

    progress = 0
    if folder.file_count > 0:
        progress = int((folder.analyzed_count / folder.file_count) * 100)

    return {
        "folder_id": str(folder.id),
        "status": folder.status.value,
        "progress": progress,
        "file_count": folder.file_count,
        "analyzed_count": folder.analyzed_count,
        "pending_count": folder.pending_count,
        "last_scan_at": folder.last_scan_at.isoformat() if folder.last_scan_at else None
    }
