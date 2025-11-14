"""
API endpoints for rename suggestions management (JSPOW v2)
"""
import logging
from typing import List, Optional
from uuid import UUID
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from pydantic import BaseModel

from app.database import get_db
from app.models import (
    RenameSuggestion,
    SuggestionStatus,
    WatchedFolder,
    Image,
    ActivityLog,
    ActivityActionType
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v2/suggestions", tags=["Suggestions v2"])


# ============================================================================
# Request/Response Models
# ============================================================================

class SuggestionResponse(BaseModel):
    id: str
    watched_folder_id: str
    watched_folder_name: str
    asset_id: Optional[int] = None
    original_path: str
    original_filename: str
    suggested_filename: str
    description: Optional[str] = None
    confidence_score: Optional[float] = None
    status: str
    created_at: str
    updated_at: Optional[str] = None


class SuggestionUpdateRequest(BaseModel):
    suggested_filename: str


class BatchActionRequest(BaseModel):
    suggestion_ids: List[str]


class SuggestionsFilterParams(BaseModel):
    folder_id: Optional[UUID] = None
    status: Optional[SuggestionStatus] = None
    min_confidence: Optional[float] = None
    limit: int = 100
    offset: int = 0


# ============================================================================
# Suggestion Endpoints
# ============================================================================

@router.get("", response_model=List[SuggestionResponse])
async def list_suggestions(
    folder_id: Optional[UUID] = None,
    status_filter: Optional[SuggestionStatus] = None,
    min_confidence: Optional[float] = None,
    limit: int = 100,
    offset: int = 0,
    db: AsyncSession = Depends(get_db)
):
    """
    List pending rename suggestions with optional filters
    """
    query = (
        select(RenameSuggestion)
        .options(selectinload(RenameSuggestion.watched_folder))
        .order_by(RenameSuggestion.created_at.desc())
    )

    # Apply filters
    if folder_id:
        query = query.where(RenameSuggestion.watched_folder_id == folder_id)

    if status_filter:
        query = query.where(RenameSuggestion.status == status_filter)
    else:
        # Default to pending suggestions
        query = query.where(RenameSuggestion.status == SuggestionStatus.PENDING)

    if min_confidence is not None:
        query = query.where(RenameSuggestion.confidence_score >= min_confidence)

    # Pagination
    query = query.limit(limit).offset(offset)

    result = await db.execute(query)
    suggestions = result.scalars().all()

    return [
        SuggestionResponse(
            id=str(suggestion.id),
            watched_folder_id=str(suggestion.watched_folder_id),
            watched_folder_name=suggestion.watched_folder.name if suggestion.watched_folder else "Unknown",
            asset_id=suggestion.asset_id,
            original_path=suggestion.original_path,
            original_filename=suggestion.original_filename,
            suggested_filename=suggestion.suggested_filename,
            description=suggestion.description,
            confidence_score=suggestion.confidence_score,
            status=suggestion.status.value,
            created_at=suggestion.created_at.isoformat(),
            updated_at=suggestion.updated_at.isoformat() if suggestion.updated_at else None
        )
        for suggestion in suggestions
    ]


@router.get("/{suggestion_id}", response_model=SuggestionResponse)
async def get_suggestion(
    suggestion_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Get details of a specific suggestion
    """
    result = await db.execute(
        select(RenameSuggestion)
        .options(selectinload(RenameSuggestion.watched_folder))
        .where(RenameSuggestion.id == suggestion_id)
    )
    suggestion = result.scalar_one_or_none()

    if not suggestion:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Suggestion not found"
        )

    return SuggestionResponse(
        id=str(suggestion.id),
        watched_folder_id=str(suggestion.watched_folder_id),
        watched_folder_name=suggestion.watched_folder.name if suggestion.watched_folder else "Unknown",
        asset_id=suggestion.asset_id,
        original_path=suggestion.original_path,
        original_filename=suggestion.original_filename,
        suggested_filename=suggestion.suggested_filename,
        description=suggestion.description,
        confidence_score=suggestion.confidence_score,
        status=suggestion.status.value,
        created_at=suggestion.created_at.isoformat(),
        updated_at=suggestion.updated_at.isoformat() if suggestion.updated_at else None
    )


@router.patch("/{suggestion_id}", response_model=SuggestionResponse)
async def update_suggestion(
    suggestion_id: UUID,
    request: SuggestionUpdateRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Edit the suggested filename for a suggestion
    """
    result = await db.execute(
        select(RenameSuggestion)
        .options(selectinload(RenameSuggestion.watched_folder))
        .where(RenameSuggestion.id == suggestion_id)
    )
    suggestion = result.scalar_one_or_none()

    if not suggestion:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Suggestion not found"
        )

    if suggestion.status != SuggestionStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can only edit pending suggestions"
        )

    suggestion.suggested_filename = request.suggested_filename
    await db.commit()
    await db.refresh(suggestion)

    return SuggestionResponse(
        id=str(suggestion.id),
        watched_folder_id=str(suggestion.watched_folder_id),
        watched_folder_name=suggestion.watched_folder.name if suggestion.watched_folder else "Unknown",
        asset_id=suggestion.asset_id,
        original_path=suggestion.original_path,
        original_filename=suggestion.original_filename,
        suggested_filename=suggestion.suggested_filename,
        description=suggestion.description,
        confidence_score=suggestion.confidence_score,
        status=suggestion.status.value,
        created_at=suggestion.created_at.isoformat(),
        updated_at=suggestion.updated_at.isoformat() if suggestion.updated_at else None
    )


@router.post("/{suggestion_id}/approve")
async def approve_suggestion(
    suggestion_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Approve a single suggestion (marks it for execution)
    """
    result = await db.execute(
        select(RenameSuggestion).where(RenameSuggestion.id == suggestion_id)
    )
    suggestion = result.scalar_one_or_none()

    if not suggestion:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Suggestion not found"
        )

    if suggestion.status != SuggestionStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can only approve pending suggestions"
        )

    suggestion.status = SuggestionStatus.APPROVED
    await db.commit()

    # Create activity log
    activity_log = ActivityLog(
        watched_folder_id=suggestion.watched_folder_id,
        asset_id=suggestion.asset_id,
        action_type=ActivityActionType.APPROVE,
        original_filename=suggestion.original_filename,
        new_filename=suggestion.suggested_filename,
        folder_path=suggestion.original_path,
        status="success"
    )
    db.add(activity_log)
    await db.commit()

    # TODO: Queue for actual rename execution
    # This will be handled by the background worker

    return {
        "message": "Suggestion approved",
        "suggestion_id": str(suggestion_id)
    }


@router.post("/{suggestion_id}/reject")
async def reject_suggestion(
    suggestion_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Reject a single suggestion
    """
    result = await db.execute(
        select(RenameSuggestion).where(RenameSuggestion.id == suggestion_id)
    )
    suggestion = result.scalar_one_or_none()

    if not suggestion:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Suggestion not found"
        )

    if suggestion.status != SuggestionStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can only reject pending suggestions"
        )

    suggestion.status = SuggestionStatus.REJECTED
    await db.commit()

    # Create activity log
    activity_log = ActivityLog(
        watched_folder_id=suggestion.watched_folder_id,
        asset_id=suggestion.asset_id,
        action_type=ActivityActionType.REJECT,
        original_filename=suggestion.original_filename,
        new_filename=suggestion.suggested_filename,
        folder_path=suggestion.original_path,
        status="success"
    )
    db.add(activity_log)
    await db.commit()

    return {
        "message": "Suggestion rejected",
        "suggestion_id": str(suggestion_id)
    }


@router.post("/batch-approve")
async def batch_approve_suggestions(
    request: BatchActionRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Approve multiple suggestions at once
    """
    suggestion_uuids = [UUID(sid) for sid in request.suggestion_ids]

    result = await db.execute(
        select(RenameSuggestion).where(
            and_(
                RenameSuggestion.id.in_(suggestion_uuids),
                RenameSuggestion.status == SuggestionStatus.PENDING
            )
        )
    )
    suggestions = result.scalars().all()

    approved_count = 0
    for suggestion in suggestions:
        suggestion.status = SuggestionStatus.APPROVED

        # Create activity log
        activity_log = ActivityLog(
            watched_folder_id=suggestion.watched_folder_id,
            asset_id=suggestion.asset_id,
            action_type=ActivityActionType.APPROVE,
            original_filename=suggestion.original_filename,
            new_filename=suggestion.suggested_filename,
            folder_path=suggestion.original_path,
            status="success"
        )
        db.add(activity_log)
        approved_count += 1

    await db.commit()

    return {
        "message": f"Approved {approved_count} suggestions",
        "approved_count": approved_count,
        "total_requested": len(request.suggestion_ids)
    }


@router.post("/batch-reject")
async def batch_reject_suggestions(
    request: BatchActionRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Reject multiple suggestions at once
    """
    suggestion_uuids = [UUID(sid) for sid in request.suggestion_ids]

    result = await db.execute(
        select(RenameSuggestion).where(
            and_(
                RenameSuggestion.id.in_(suggestion_uuids),
                RenameSuggestion.status == SuggestionStatus.PENDING
            )
        )
    )
    suggestions = result.scalars().all()

    rejected_count = 0
    for suggestion in suggestions:
        suggestion.status = SuggestionStatus.REJECTED

        # Create activity log
        activity_log = ActivityLog(
            watched_folder_id=suggestion.watched_folder_id,
            asset_id=suggestion.asset_id,
            action_type=ActivityActionType.REJECT,
            original_filename=suggestion.original_filename,
            new_filename=suggestion.suggested_filename,
            folder_path=suggestion.original_path,
            status="success"
        )
        db.add(activity_log)
        rejected_count += 1

    await db.commit()

    return {
        "message": f"Rejected {rejected_count} suggestions",
        "rejected_count": rejected_count,
        "total_requested": len(request.suggestion_ids)
    }


@router.get("/stats/summary")
async def get_suggestions_stats(db: AsyncSession = Depends(get_db)):
    """
    Get aggregate statistics for rename suggestions
    """
    # Count by status
    status_counts = await db.execute(
        select(
            RenameSuggestion.status,
            func.count(RenameSuggestion.id)
        ).group_by(RenameSuggestion.status)
    )
    status_map = {status: count for status, count in status_counts}

    # Average confidence
    avg_confidence = await db.execute(
        select(func.avg(RenameSuggestion.confidence_score))
        .where(RenameSuggestion.status == SuggestionStatus.PENDING)
    )
    avg_conf = avg_confidence.scalar() or 0.0

    return {
        "total": sum(status_map.values()),
        "pending": status_map.get(SuggestionStatus.PENDING, 0),
        "approved": status_map.get(SuggestionStatus.APPROVED, 0),
        "rejected": status_map.get(SuggestionStatus.REJECTED, 0),
        "applied": status_map.get(SuggestionStatus.APPLIED, 0),
        "failed": status_map.get(SuggestionStatus.FAILED, 0),
        "average_confidence": round(float(avg_conf), 2)
    }
