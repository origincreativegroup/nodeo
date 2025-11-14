"""
API endpoints for activity log (JSPOW v2)
"""
import logging
from typing import List, Optional
from uuid import UUID
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy import select, and_, or_, func
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
import csv
import io
import json

from app.database import get_db
from app.models import (
    ActivityLog,
    ActivityActionType,
    WatchedFolder
)
from app.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v2/activity", tags=["Activity v2"])


# ============================================================================
# Request/Response Models
# ============================================================================

class ActivityLogResponse(BaseModel):
    id: str
    watched_folder_id: Optional[str] = None
    watched_folder_name: Optional[str] = None
    asset_id: Optional[int] = None
    action_type: str
    original_filename: Optional[str] = None
    new_filename: Optional[str] = None
    folder_path: Optional[str] = None
    status: str
    error_message: Optional[str] = None
    metadata: Optional[dict] = None
    created_at: str


class ActivityFilterParams(BaseModel):
    folder_id: Optional[UUID] = None
    action_type: Optional[ActivityActionType] = None
    status: Optional[str] = None  # success, failure
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    limit: int = 100
    offset: int = 0


# ============================================================================
# Activity Log Endpoints
# ============================================================================

@router.get("", response_model=List[ActivityLogResponse])
async def list_activity_log(
    folder_id: Optional[UUID] = None,
    action_type: Optional[ActivityActionType] = None,
    status_filter: Optional[str] = None,
    days: int = 7,
    limit: int = 100,
    offset: int = 0,
    db: AsyncSession = Depends(get_db)
):
    """
    List activity log entries with optional filters
    """
    query = (
        select(ActivityLog)
        .order_by(ActivityLog.created_at.desc())
    )

    # Apply filters
    conditions = []

    if folder_id:
        conditions.append(ActivityLog.watched_folder_id == folder_id)

    if action_type:
        conditions.append(ActivityLog.action_type == action_type)

    if status_filter:
        conditions.append(ActivityLog.status == status_filter)

    # Date range filter
    if days > 0:
        since_date = datetime.utcnow() - timedelta(days=days)
        conditions.append(ActivityLog.created_at >= since_date)

    if conditions:
        query = query.where(and_(*conditions))

    # Pagination
    query = query.limit(limit).offset(offset)

    result = await db.execute(query)
    logs = result.scalars().all()

    # Get folder names
    folder_ids = [log.watched_folder_id for log in logs if log.watched_folder_id]
    if folder_ids:
        folder_result = await db.execute(
            select(WatchedFolder).where(WatchedFolder.id.in_(folder_ids))
        )
        folders = {f.id: f.name for f in folder_result.scalars().all()}
    else:
        folders = {}

    return [
        ActivityLogResponse(
            id=str(log.id),
            watched_folder_id=str(log.watched_folder_id) if log.watched_folder_id else None,
            watched_folder_name=folders.get(log.watched_folder_id),
            asset_id=log.asset_id,
            action_type=log.action_type.value,
            original_filename=log.original_filename,
            new_filename=log.new_filename,
            folder_path=log.folder_path,
            status=log.status,
            error_message=log.error_message,
            metadata=log.metadata,
            created_at=log.created_at.isoformat()
        )
        for log in logs
    ]


@router.get("/stats")
async def get_activity_stats(
    days: int = 7,
    db: AsyncSession = Depends(get_db)
):
    """
    Get activity statistics
    """
    since_date = datetime.utcnow() - timedelta(days=days)

    # Count by action type
    action_counts = await db.execute(
        select(
            ActivityLog.action_type,
            func.count(ActivityLog.id)
        )
        .where(ActivityLog.created_at >= since_date)
        .group_by(ActivityLog.action_type)
    )
    action_map = {action.value: count for action, count in action_counts}

    # Count by status
    status_counts = await db.execute(
        select(
            ActivityLog.status,
            func.count(ActivityLog.id)
        )
        .where(ActivityLog.created_at >= since_date)
        .group_by(ActivityLog.status)
    )
    status_map = {status: count for status, count in status_counts}

    # Total count
    total = await db.execute(
        select(func.count(ActivityLog.id))
        .where(ActivityLog.created_at >= since_date)
    )
    total_count = total.scalar()

    return {
        "period_days": days,
        "total_activities": total_count,
        "by_action": action_map,
        "by_status": status_map,
        "success_rate": round(
            (status_map.get("success", 0) / total_count * 100) if total_count > 0 else 0,
            2
        )
    }


@router.get("/export")
async def export_activity_log(
    format: str = "csv",
    days: int = 30,
    db: AsyncSession = Depends(get_db)
):
    """
    Export activity log as CSV or JSON
    """
    since_date = datetime.utcnow() - timedelta(days=days)

    result = await db.execute(
        select(ActivityLog)
        .where(ActivityLog.created_at >= since_date)
        .order_by(ActivityLog.created_at.desc())
    )
    logs = result.scalars().all()

    if format == "json":
        # Export as JSON
        data = [
            {
                "id": str(log.id),
                "action_type": log.action_type.value,
                "status": log.status,
                "original_filename": log.original_filename,
                "new_filename": log.new_filename,
                "folder_path": log.folder_path,
                "error_message": log.error_message,
                "created_at": log.created_at.isoformat()
            }
            for log in logs
        ]

        return Response(
            content=json.dumps(data, indent=2),
            media_type="application/json",
            headers={
                "Content-Disposition": f"attachment; filename=activity_log_{datetime.utcnow().strftime('%Y%m%d')}.json"
            }
        )

    else:  # CSV
        # Export as CSV
        output = io.StringIO()
        writer = csv.writer(output)

        # Write header
        writer.writerow([
            "ID",
            "Action Type",
            "Status",
            "Original Filename",
            "New Filename",
            "Folder Path",
            "Error Message",
            "Created At"
        ])

        # Write data
        for log in logs:
            writer.writerow([
                str(log.id),
                log.action_type.value,
                log.status,
                log.original_filename or "",
                log.new_filename or "",
                log.folder_path or "",
                log.error_message or "",
                log.created_at.isoformat()
            ])

        return Response(
            content=output.getvalue(),
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename=activity_log_{datetime.utcnow().strftime('%Y%m%d')}.csv"
            }
        )


@router.delete("/cleanup")
async def cleanup_old_logs(
    days: Optional[int] = None,
    db: AsyncSession = Depends(get_db)
):
    """
    Delete activity logs older than specified days (defaults to configured retention)
    """
    retention_days = days if days is not None else settings.activity_log_retention_days
    cutoff_date = datetime.utcnow() - timedelta(days=retention_days)

    # Count logs to be deleted
    count_result = await db.execute(
        select(func.count(ActivityLog.id))
        .where(ActivityLog.created_at < cutoff_date)
    )
    count = count_result.scalar()

    # Delete old logs
    await db.execute(
        ActivityLog.__table__.delete().where(ActivityLog.created_at < cutoff_date)
    )
    await db.commit()

    return {
        "message": f"Deleted {count} activity log entries older than {retention_days} days",
        "deleted_count": count,
        "cutoff_date": cutoff_date.isoformat()
    }


@router.post("/{activity_id}/rollback")
async def rollback_rename(
    activity_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Rollback a rename operation using its activity log entry
    """
    from app.workers.rename_executor import rename_executor

    result = await rename_executor.rollback_rename(activity_id)

    if not result["success"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.get("error", "Failed to rollback rename")
        )

    return result
