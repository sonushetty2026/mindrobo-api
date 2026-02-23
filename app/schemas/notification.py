"""Pydantic schemas for notifications."""

from pydantic import BaseModel
from uuid import UUID
from datetime import datetime
from app.models.notification import NotificationType


class NotificationOut(BaseModel):
    """Response schema for notification."""
    id: UUID
    user_id: UUID
    title: str
    message: str
    type: NotificationType
    is_read: bool
    created_at: datetime

    class Config:
        from_attributes = True


class NotificationList(BaseModel):
    """Response schema for paginated notifications."""
    notifications: list[NotificationOut]
    total: int
    page: int
    page_size: int


class NotificationUnreadCount(BaseModel):
    """Response schema for unread notification count."""
    count: int


class BroadcastRequest(BaseModel):
    """Request schema for admin broadcast notification."""
    title: str
    message: str
    type: NotificationType = NotificationType.ADMIN
    target_role: str | None = None  # Optional: filter by role (e.g., "user", "admin")


class TrialStatusResponse(BaseModel):
    """Response schema for trial status."""
    is_trial: bool
    trial_ends_at: datetime | None
    days_remaining: int | None
    is_paused: bool
    in_grace_period: bool


class UsageLimitsResponse(BaseModel):
    """Response schema for trial usage limits."""
    calls_used: int
    calls_limit: int
    leads_used: int
    leads_limit: int
    appointments_used: int
    appointments_limit: int
    is_trial: bool


class FCMTokenRequest(BaseModel):
    """Request schema for FCM token registration."""
    fcm_token: str
