"""Notification service for creating and sending notifications."""

import logging
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import Notification, NotificationType
from app.models.user import User

logger = logging.getLogger(__name__)


async def create_notification(
    db: AsyncSession,
    user_id: UUID,
    title: str,
    message: str,
    notification_type: NotificationType,
) -> Notification:
    """Create a notification for a user.
    
    This is a reusable service function that can be called from anywhere
    (signup, trial expiry, payment failed, etc.).
    """
    notification = Notification(
        user_id=user_id,
        title=title,
        message=message,
        type=notification_type,
        is_read=False,
    )
    db.add(notification)
    await db.commit()
    await db.refresh(notification)
    
    logger.info(
        "Created notification for user %s: %s (%s)",
        user_id,
        title,
        notification_type.value,
    )
    
    # Stub: FCM push notification (log only, no actual sending)
    await send_fcm_push_stub(user_id, title, message, db)
    
    return notification


async def send_fcm_push_stub(
    user_id: UUID,
    title: str,
    message: str,
    db: AsyncSession,
):
    """Stub for FCM push notification sending.
    
    Logs to console instead of actually sending via Firebase SDK.
    """
    from sqlalchemy import select
    
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if user and user.fcm_token:
        logger.info(
            "📱 FCM PUSH would be sent to user %s (token: %s...): %s - %s",
            user.email,
            user.fcm_token[:20] if user.fcm_token else "none",
            title,
            message,
        )
    else:
        logger.debug(
            "📱 FCM PUSH skipped for user %s (no FCM token registered)",
            user_id,
        )


async def create_welcome_notification(db: AsyncSession, user_id: UUID):
    """Create a welcome notification for a new user."""
    await create_notification(
        db=db,
        user_id=user_id,
        title="Welcome to MindRobo! 🚀",
        message="Your 14-day free trial has started. Explore all features and see how MindRobo can transform your business.",
        notification_type=NotificationType.SYSTEM,
    )


async def create_trial_expiry_warning(db: AsyncSession, user_id: UUID, days_left: int):
    """Create a trial expiry warning notification."""
    await create_notification(
        db=db,
        user_id=user_id,
        title=f"⏰ Trial Ending in {days_left} Days",
        message=f"Your free trial will expire in {days_left} days. Upgrade now to continue using MindRobo without interruption.",
        notification_type=NotificationType.TRIAL,
    )


async def create_trial_expired_notification(db: AsyncSession, user_id: UUID):
    """Create a trial expired notification."""
    await create_notification(
        db=db,
        user_id=user_id,
        title="Trial Expired",
        message="Your 14-day trial has ended. You have a 3-day grace period. Please upgrade to continue using MindRobo.",
        notification_type=NotificationType.TRIAL,
    )


async def create_payment_failed_notification(db: AsyncSession, user_id: UUID):
    """Create a payment failed notification."""
    await create_notification(
        db=db,
        user_id=user_id,
        title="Payment Failed",
        message="We couldn't process your payment. Please update your payment method to avoid service interruption.",
        notification_type=NotificationType.BILLING,
    )
