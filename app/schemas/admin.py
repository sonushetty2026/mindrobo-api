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


class AdminTrialConvert(BaseModel):
    """Convert trial user to paid."""
    plan_id: UUID = Field(description="Subscription plan ID to assign")


# API Usage tracking schemas (Issues #92, #93)
class UsageSummary(BaseModel):
    """Platform-wide API usage summary."""
    total_spend: int = Field(description="Total platform spend in cents")
    retell_cost: int = Field(description="Retell API cost in cents")
    twilio_cost: int = Field(description="Twilio API cost in cents")
    sendgrid_cost: int = Field(description="SendGrid API cost in cents")


class UserUsage(BaseModel):
    """Per-user usage breakdown."""
    user_email: str
    user_id: str
    total_cost: int = Field(description="Total cost in cents")
    retell_cost: int = Field(description="Retell cost in cents")
    twilio_cost: int = Field(description="Twilio cost in cents")
    sendgrid_cost: int = Field(description="SendGrid cost in cents")


class UserMargin(BaseModel):
    """Per-user margin analysis."""
    user_email: str
    user_id: str
    plan_price: int = Field(description="Monthly plan price in cents")
    total_cost: int = Field(description="Total API cost in cents")
    margin: int = Field(description="Profit margin in cents")
    margin_percent: float = Field(description="Margin as percentage")
    alert: bool = Field(description="True if cost exceeds plan price")


class DailyCostTrend(BaseModel):
    """Daily cost trend data point."""
    date: str = Field(description="Date in YYYY-MM-DD format")
    total_cost: int = Field(description="Total cost for that day in cents")


class UsageTrends(BaseModel):
    """Cost trends over time."""
    days: int = Field(description="Number of days of data")
    trends: List[DailyCostTrend]


# Audit Log schemas (Issue #94)
class AuditLogEntry(BaseModel):
    """Single audit log entry."""
    id: UUID
    admin_id: UUID
    action: str
    target_user_id: Optional[UUID]
    details: Optional[dict]
    created_at: datetime
    admin_email: Optional[str] = None
    target_email: Optional[str] = None

    class Config:
        from_attributes = True


class AuditLogList(BaseModel):
    """Paginated audit log list."""
    logs: List[AuditLogEntry]
    total: int
    limit: int
    offset: int


# Impersonation schema (Issue #95)
class ImpersonationResponse(BaseModel):
    """Impersonation JWT response."""
    access_token: str
    token_type: str = "bearer"
    impersonated_user_id: UUID
    impersonated_email: str
    expires_in: int = Field(description="Token expiry in seconds")


# Integration Health schema (Issue #96)
class IntegrationStatus(BaseModel):
    """Single integration health status."""
    status: str = Field(description="ok, not_configured, or error")
    message: Optional[str] = None


class HealthCheckResponse(BaseModel):
    """Integration health check response."""
    db: IntegrationStatus
    retell: IntegrationStatus
    twilio: IntegrationStatus
    stripe: IntegrationStatus
    sendgrid: IntegrationStatus


# Onboarding Funnel schemas (Issue #97)
class OnboardingStageCount(BaseModel):
    """Count of users at each onboarding stage."""
    stage: str
    count: int
    drop_off_percent: Optional[float] = None


class OnboardingFunnelResponse(BaseModel):
    """Onboarding funnel analytics."""
    stages: List[OnboardingStageCount]
    total_signups: int
    overall_completion_rate: float
