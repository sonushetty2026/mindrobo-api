"""Pydantic schemas for admin endpoints."""

from datetime import datetime
from typing import Optional, List
from uuid import UUID
from pydantic import BaseModel, Field


# Analytics schemas
class AdminAnalytics(BaseModel):
    """Admin dashboard analytics."""
    total_users: int
    signups_today: int
    signups_this_week: int
    signups_this_month: int
    active_users: int = Field(description="Users who logged in within last 7 days")
    mrr: int = Field(description="Monthly Recurring Revenue in cents")
    total_revenue: int = Field(description="Total revenue in cents")
    trial_users: int
    paid_users: int
    expired_users: int = Field(description="Users whose trial expired")


# User management schemas
class AdminUserOut(BaseModel):
    """User details for admin view."""
    id: UUID
    email: str
    full_name: Optional[str]
    role: str
    is_active: bool
    is_verified: bool
    is_trial: bool
    trial_ends_at: Optional[datetime]
    is_paused: bool
    paused_at: Optional[datetime]
    plan_id: Optional[UUID]
    last_login_at: Optional[datetime]
    created_at: datetime
    business_id: UUID

    class Config:
        from_attributes = True


class AdminUserList(BaseModel):
    """Paginated user list."""
    users: List[AdminUserOut]
    total: int
    limit: int
    offset: int


class AdminUserUpdate(BaseModel):
    """Update user fields (admin only)."""
    role: Optional[str] = Field(None, pattern="^(user|admin|superadmin)$")
    is_paused: Optional[bool] = None
    plan_id: Optional[UUID] = None


class MessageResponse(BaseModel):
    """Generic message response."""
    message: str


# Trial management schemas
class AdminTrialUser(BaseModel):
    """Trial user info."""
    id: UUID
    email: str
    full_name: Optional[str]
    trial_ends_at: Optional[datetime]
    days_remaining: Optional[int] = Field(description="Days until trial expires, null if expired")
    created_at: datetime
    last_login_at: Optional[datetime]

    class Config:
        from_attributes = True


class AdminTrialList(BaseModel):
    """Paginated trial user list."""
    trials: List[AdminTrialUser]
    total: int
    limit: int
    offset: int


class AdminTrialStats(BaseModel):
    """Trial statistics."""
    conversion_rate: float = Field(description="Percentage of trials converted to paid")
    avg_trial_length: float = Field(description="Average trial duration in days")
    active_trials: int
    expired_trials: int


class AdminTrialExtend(BaseModel):
    """Extend or shorten trial."""
    days: int = Field(description="Number of days to extend (positive) or shorten (negative)")
