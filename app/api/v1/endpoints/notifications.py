"""Notification endpoints for MindRobo."""

import logging
from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy import select, func, update
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from app.core.database import get_db
from app.core.deps import get_current_user, check_trial_status
from app.models.user import User
from app.models.notification import Notification
from app.schemas.notification import (
    NotificationOut,
    NotificationList,
    NotificationUnreadCount,
)
from app.schemas.auth import MessageResponse

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/", response_model=NotificationList)
async def list_notifications(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(check_trial_status),
    db: AsyncSession = Depends(get_db),
):
    """List user's notifications (paginated, newest first).
    
    Protected by trial check.
    """
    offset = (page - 1) * page_size
    
    # Get total count
    count_query = select(func.count(Notification.id)).where(
        Notification.user_id == current_user.id
    )
    count_result = await db.execute(count_query)
    total = count_result.scalar_one()
    
    # Get notifications
    query = (
        select(Notification)
        .where(Notification.user_id == current_user.id)
        .order_by(Notification.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    result = await db.execute(query)
    notifications = result.scalars().all()
    
    return NotificationList(
        notifications=[NotificationOut.model_validate(n) for n in notifications],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/unread-count", response_model=NotificationUnreadCount)
async def get_unread_count(
    current_user: User = Depends(check_trial_status),
    db: AsyncSession = Depends(get_db),
):
    """Get count of unread notifications.
    
    Protected by trial check.
    """
    query = select(func.count(Notification.id)).where(
        Notification.user_id == current_user.id,
        Notification.is_read == False,
    )
    result = await db.execute(query)
    count = result.scalar_one()
    
    return NotificationUnreadCount(count=count)


@router.put("/{notification_id}/read", response_model=MessageResponse)
async def mark_notification_read(
    notification_id: UUID,
    current_user: User = Depends(check_trial_status),
    db: AsyncSession = Depends(get_db),
):
    """Mark a notification as read.
    
    Protected by trial check.
    """
    query = select(Notification).where(
        Notification.id == notification_id,
        Notification.user_id == current_user.id,
    )
    result = await db.execute(query)
    notification = result.scalar_one_or_none()
    
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
    
    notification.is_read = True
    await db.commit()
    
    logger.info("Notification %s marked as read by user %s", notification_id, current_user.id)
    
    return MessageResponse(message="Notification marked as read")


@router.put("/mark-all-read", response_model=MessageResponse)
async def mark_all_notifications_read(
    current_user: User = Depends(check_trial_status),
    db: AsyncSession = Depends(get_db),
):
    """Mark all user's notifications as read.
    
    Protected by trial check.
    """
    stmt = (
        update(Notification)
        .where(
            Notification.user_id == current_user.id,
            Notification.is_read == False,
        )
        .values(is_read=True)
    )
    result = await db.execute(stmt)
    await db.commit()
    
    updated_count = result.rowcount
    
    logger.info("Marked %d notifications as read for user %s", updated_count, current_user.id)
    
    return MessageResponse(message=f"Marked {updated_count} notifications as read")
