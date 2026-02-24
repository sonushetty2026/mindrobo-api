"""Admin-only endpoints for MindRobo API.

All routes require superadmin role.
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, desc

from app.core.database import get_db
from app.core.dependencies import require_superadmin, require_support
from app.core.auth import create_access_token
from app.models.user import User
from app.models.subscription_plan import SubscriptionPlan
from app.models.admin_audit_log import AdminAuditLog
from app.models.call import Call
from app.models.business import Business
from app.schemas.admin import (
    AdminAnalytics,
    AdminUserOut,
    AdminUserList,
    AdminUserUpdate,
    AdminTrialUser,
    AdminTrialList,
    AdminTrialStats,
    AdminTrialExtend,
    AdminTrialConvert,
    MessageResponse,
    UsageSummary,
    UserUsage,
    UserMargin,
    UsageTrends,
    DailyCostTrend,
    AuditLogEntry,
    AuditLogList,
    ImpersonationResponse,
    HealthCheckResponse,
    IntegrationStatus,
    OnboardingFunnelResponse,
    OnboardingStageCount,
)
from app.schemas.notification import BroadcastRequest
from app.services.notification_service import create_notification
from app.services.audit_service import log_admin_action
from app.models.notification import NotificationType

router = APIRouter()
logger = logging.getLogger(__name__)


# ============================================================================
# ISSUE #84: ADMIN DASHBOARD ANALYTICS
# ============================================================================

@router.get("/analytics", response_model=AdminAnalytics)
async def get_admin_analytics(
    current_user: User = Depends(require_superadmin),
    db: AsyncSession = Depends(get_db)
):
    """Get admin dashboard analytics.
    
    Returns: total_users, signups_today/week/month, active_users (last 7 days),
    MRR, total_revenue, trial_users, paid_users, expired_users.
    """
    now = datetime.utcnow()
    today_start = datetime(now.year, now.month, now.day)
    week_start = now - timedelta(days=7)
    month_start = datetime(now.year, now.month, 1)
    
    # Total users
    total_users_result = await db.execute(select(func.count(User.id)))
    total_users = total_users_result.scalar() or 0
    
    # Signups today
    signups_today_result = await db.execute(
        select(func.count(User.id)).where(User.created_at >= today_start)
    )
    signups_today = signups_today_result.scalar() or 0
    
    # Signups this week
    signups_week_result = await db.execute(
        select(func.count(User.id)).where(User.created_at >= week_start)
    )
    signups_this_week = signups_week_result.scalar() or 0
    
    # Signups this month
    signups_month_result = await db.execute(
        select(func.count(User.id)).where(User.created_at >= month_start)
    )
    signups_this_month = signups_month_result.scalar() or 0
    
    # Active users (logged in last 7 days)
    active_users_result = await db.execute(
        select(func.count(User.id)).where(
            User.last_login_at >= week_start
        )
    )
    active_users = active_users_result.scalar() or 0
    
    # Trial users
    trial_users_result = await db.execute(
        select(func.count(User.id)).where(User.is_trial == True)
    )
    trial_users = trial_users_result.scalar() or 0
    
    # Paid users (not on trial)
    paid_users_result = await db.execute(
        select(func.count(User.id)).where(User.is_trial == False)
    )
    paid_users = paid_users_result.scalar() or 0
    
    # Expired users (trial ended but still on trial flag)
    expired_users_result = await db.execute(
        select(func.count(User.id)).where(
            and_(
                User.is_trial == True,
                User.trial_ends_at < now
            )
        )
    )
    expired_users = expired_users_result.scalar() or 0
    
    # MRR and total revenue calculation
    # For now, we'll compute based on paid users and their plans
    # MRR = sum of all active paid user plan prices
    paid_users_with_plans = await db.execute(
        select(User, SubscriptionPlan).join(
            SubscriptionPlan, User.plan_id == SubscriptionPlan.id
        ).where(User.is_trial == False)
    )
    
    mrr = 0
    total_revenue = 0
    for user, plan in paid_users_with_plans:
        mrr += plan.price_cents
        # Total revenue could be calculated differently (e.g., from billing records)
        # For now, we'll use MRR as a proxy
    
    total_revenue = mrr  # Simplified: could integrate with billing logs
    
    return AdminAnalytics(
        total_users=total_users,
        signups_today=signups_today,
        signups_this_week=signups_this_week,
        signups_this_month=signups_this_month,
        active_users=active_users,
        mrr=mrr,
        total_revenue=total_revenue,
        trial_users=trial_users,
        paid_users=paid_users,
        expired_users=expired_users,
    )


# ============================================================================
# ISSUE #85: ADMIN USER MANAGEMENT
# ============================================================================

@router.get("/users", response_model=AdminUserList)
async def list_users(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    role: Optional[str] = Query(None, pattern="^(user|admin|superadmin)$"),
    is_trial: Optional[bool] = None,
    is_active: Optional[bool] = None,
    current_user: User = Depends(require_superadmin),
    db: AsyncSession = Depends(get_db)
):
    """List all users with pagination and filtering.
    
    Query params:
    - limit: max results per page (default 50, max 500)
    - offset: pagination offset
    - role: filter by role (user|admin|superadmin)
    - is_trial: filter by trial status
    - is_active: filter by active status
    """
    # Build query with filters
    query = select(User)
    filters = []
    
    if role:
        filters.append(User.role == role)
    if is_trial is not None:
        filters.append(User.is_trial == is_trial)
    if is_active is not None:
        filters.append(User.is_active == is_active)
    
    if filters:
        query = query.where(and_(*filters))
    
    # Get total count
    count_query = select(func.count(User.id))
    if filters:
        count_query = count_query.where(and_(*filters))
    
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0
    
    # Get paginated results
    query = query.order_by(User.created_at.desc()).limit(limit).offset(offset)
    result = await db.execute(query)
    users = result.scalars().all()
    
    return AdminUserList(
        users=[AdminUserOut.model_validate(user) for user in users],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/users/{user_id}", response_model=AdminUserOut)
async def get_user_details(
    user_id: UUID,
    current_user: User = Depends(require_superadmin),
    db: AsyncSession = Depends(get_db)
):
    """Get single user details."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return AdminUserOut.model_validate(user)


@router.put("/users/{user_id}", response_model=AdminUserOut)
async def update_user(
    user_id: UUID,
    update_data: AdminUserUpdate,
    current_user: User = Depends(require_superadmin),
    db: AsyncSession = Depends(get_db)
):
    """Update user fields (role, is_paused, plan_id).
    
    Admin can modify user roles, pause status, and subscription plan.
    """
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Apply updates
    if update_data.role is not None:
        user.role = update_data.role
        logger.info("Admin %s changed user %s role to %s", current_user.email, user.email, update_data.role)
    
    if update_data.is_paused is not None:
        user.is_paused = update_data.is_paused
        user.paused_at = datetime.utcnow() if update_data.is_paused else None
        logger.info("Admin %s %s user %s", current_user.email, "paused" if update_data.is_paused else "unpaused", user.email)
    
    if update_data.plan_id is not None:
        # Verify plan exists
        plan_result = await db.execute(select(SubscriptionPlan).where(SubscriptionPlan.id == update_data.plan_id))
        plan = plan_result.scalar_one_or_none()
        if not plan:
            raise HTTPException(status_code=404, detail="Subscription plan not found")
        
        user.plan_id = update_data.plan_id
        logger.info("Admin %s assigned plan %s to user %s", current_user.email, plan.name, user.email)
    
    await db.commit()
    await db.refresh(user)
    
    return AdminUserOut.model_validate(user)


@router.post("/users/{user_id}/pause", response_model=MessageResponse)
async def pause_user(
    user_id: UUID,
    current_user: User = Depends(require_superadmin),
    db: AsyncSession = Depends(get_db)
):
    """Pause a user account."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if user.is_paused:
        raise HTTPException(status_code=400, detail="User is already paused")
    
    user.is_paused = True
    user.paused_at = datetime.utcnow()
    await db.commit()
    
    # Audit log
    await log_admin_action(
        db=db,
        admin_id=current_user.id,
        action="user_pause",
        target_user_id=user.id,
        details={"user_email": user.email}
    )
    
    logger.info("Admin %s paused user %s", current_user.email, user.email)
    
    return MessageResponse(message=f"User {user.email} has been paused")


@router.post("/users/{user_id}/unpause", response_model=MessageResponse)
async def unpause_user(
    user_id: UUID,
    current_user: User = Depends(require_superadmin),
    db: AsyncSession = Depends(get_db)
):
    """Unpause a user account."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if not user.is_paused:
        raise HTTPException(status_code=400, detail="User is not paused")
    
    user.is_paused = False
    user.paused_at = None
    await db.commit()
    
    # Audit log
    await log_admin_action(
        db=db,
        admin_id=current_user.id,
        action="user_unpause",
        target_user_id=user.id,
        details={"user_email": user.email}
    )
    
    logger.info("Admin %s unpaused user %s", current_user.email, user.email)
    
    return MessageResponse(message=f"User {user.email} has been unpaused")


@router.delete("/users/{user_id}", response_model=MessageResponse)
async def soft_delete_user(
    user_id: UUID,
    current_user: User = Depends(require_superadmin),
    db: AsyncSession = Depends(get_db)
):
    """Soft delete a user (set is_active=False).
    
    Does not actually delete from database, just deactivates the account.
    """
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if not user.is_active:
        raise HTTPException(status_code=400, detail="User is already deactivated")
    
    # Prevent deleting the current admin
    if user.id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot deactivate your own account")
    
    user.is_active = False
    await db.commit()
    
    # Audit log
    await log_admin_action(
        db=db,
        admin_id=current_user.id,
        action="user_delete",
        target_user_id=user.id,
        details={"user_email": user.email}
    )
    
    logger.warning("Admin %s deactivated user %s", current_user.email, user.email)
    
    return MessageResponse(message=f"User {user.email} has been deactivated")


# ============================================================================
# ISSUE #86: ADMIN TRIAL MONITOR
# ============================================================================

@router.get("/trials", response_model=AdminTrialList)
async def list_trial_users(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(require_superadmin),
    db: AsyncSession = Depends(get_db)
):
    """List all trial users with days_remaining and trial_ends_at.
    
    Calculates days_remaining based on trial_ends_at.
    """
    now = datetime.utcnow()
    
    # Get total count
    count_result = await db.execute(
        select(func.count(User.id)).where(User.is_trial == True)
    )
    total = count_result.scalar() or 0
    
    # Get paginated trial users
    query = select(User).where(User.is_trial == True).order_by(User.trial_ends_at).limit(limit).offset(offset)
    result = await db.execute(query)
    users = result.scalars().all()
    
    # Calculate days_remaining for each user
    trial_users = []
    for user in users:
        days_remaining = None
        if user.trial_ends_at:
            delta = user.trial_ends_at - now
            days_remaining = max(0, delta.days) if delta.days >= 0 else None  # None if expired
        
        trial_users.append(AdminTrialUser(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            trial_ends_at=user.trial_ends_at,
            days_remaining=days_remaining,
            created_at=user.created_at,
            last_login_at=user.last_login_at,
        ))
    
    return AdminTrialList(
        trials=trial_users,
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/trials/stats", response_model=AdminTrialStats)
async def get_trial_stats(
    current_user: User = Depends(require_superadmin),
    db: AsyncSession = Depends(get_db)
):
    """Get trial statistics: conversion rate, avg trial length, active/expired trials."""
    now = datetime.utcnow()
    
    # Active trials (trial_ends_at in the future or null, and is_trial=True)
    active_trials_result = await db.execute(
        select(func.count(User.id)).where(
            and_(
                User.is_trial == True,
                or_(
                    User.trial_ends_at >= now,
                    User.trial_ends_at == None
                )
            )
        )
    )
    active_trials = active_trials_result.scalar() or 0
    
    # Expired trials (trial_ends_at in the past and is_trial=True)
    expired_trials_result = await db.execute(
        select(func.count(User.id)).where(
            and_(
                User.is_trial == True,
                User.trial_ends_at < now
            )
        )
    )
    expired_trials = expired_trials_result.scalar() or 0
    
    # Total users who were ever on trial
    total_trial_users_result = await db.execute(
        select(func.count(User.id)).where(User.trial_ends_at.isnot(None))
    )
    total_trial_users = total_trial_users_result.scalar() or 0
    
    # Paid users (converted from trial)
    paid_users_result = await db.execute(
        select(func.count(User.id)).where(
            and_(
                User.is_trial == False,
                User.trial_ends_at.isnot(None)  # Had a trial at some point
            )
        )
    )
    paid_users = paid_users_result.scalar() or 0
    
    # Conversion rate
    conversion_rate = (paid_users / total_trial_users * 100) if total_trial_users > 0 else 0.0
    
    # Average trial length (for users with trial_ends_at and created_at)
    avg_trial_query = await db.execute(
        select(
            func.avg(
                func.extract('epoch', User.trial_ends_at - User.created_at) / 86400
            )
        ).where(
            and_(
                User.trial_ends_at.isnot(None),
                User.created_at.isnot(None)
            )
        )
    )
    avg_trial_length = avg_trial_query.scalar() or 14.0  # Default to 14 days
    
    return AdminTrialStats(
        conversion_rate=round(conversion_rate, 2),
        avg_trial_length=round(avg_trial_length, 1),
        active_trials=active_trials,
        expired_trials=expired_trials,
    )


@router.post("/trials/{user_id}/extend", response_model=MessageResponse)
async def extend_trial(
    user_id: UUID,
    extend_data: AdminTrialExtend,
    current_user: User = Depends(require_superadmin),
    db: AsyncSession = Depends(get_db)
):
    """Extend trial by N days (or shorten if negative).
    
    Modifies trial_ends_at by adding/subtracting days.
    """
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if not user.is_trial:
        raise HTTPException(status_code=400, detail="User is not on trial")
    
    if not user.trial_ends_at:
        # If no trial_ends_at, set it to now + days
        user.trial_ends_at = datetime.utcnow() + timedelta(days=extend_data.days)
    else:
        user.trial_ends_at = user.trial_ends_at + timedelta(days=extend_data.days)
    
    await db.commit()
    
    action = "extended" if extend_data.days > 0 else "shortened"
    
    # Audit log
    await log_admin_action(
        db=db,
        admin_id=current_user.id,
        action="trial_extend" if extend_data.days > 0 else "trial_shorten",
        target_user_id=user.id,
        details={
            "user_email": user.email,
            "days": extend_data.days,
            "new_trial_ends_at": user.trial_ends_at.isoformat()
        }
    )
    
    logger.info("Admin %s %s trial for user %s by %d days", current_user.email, action, user.email, abs(extend_data.days))
    
    return MessageResponse(
        message=f"Trial {action} by {abs(extend_data.days)} days. New trial_ends_at: {user.trial_ends_at.isoformat()}"
    )


@router.post("/trials/{user_id}/shorten", response_model=MessageResponse)
async def shorten_trial(
    user_id: UUID,
    shorten_data: AdminTrialExtend,
    current_user: User = Depends(require_superadmin),
    db: AsyncSession = Depends(get_db)
):
    """Shorten trial by N days (convenience endpoint, calls extend with negative days)."""
    # Flip the sign to shorten
    shorten_data.days = -abs(shorten_data.days)
    return await extend_trial(user_id, shorten_data, current_user, db)


@router.post("/trials/{user_id}/convert", response_model=MessageResponse)
async def convert_trial_to_paid(
    user_id: UUID,
    convert_data: AdminTrialConvert,
    current_user: User = Depends(require_superadmin),
    db: AsyncSession = Depends(get_db)
):
    """Convert a trial user to paid.
    
    Sets is_trial=False, clears trial_ends_at, assigns plan_id.
    """
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if not user.is_trial:
        raise HTTPException(status_code=400, detail="User is not on trial")
    
    # Verify plan exists
    plan_result = await db.execute(select(SubscriptionPlan).where(SubscriptionPlan.id == convert_data.plan_id))
    plan = plan_result.scalar_one_or_none()
    if not plan:
        raise HTTPException(status_code=404, detail="Subscription plan not found")
    
    # Convert to paid
    user.is_trial = False
    user.trial_ends_at = None
    user.plan_id = convert_data.plan_id
    await db.commit()
    
    # Audit log
    await log_admin_action(
        db=db,
        admin_id=current_user.id,
        action="trial_convert",
        target_user_id=user.id,
        details={
            "user_email": user.email,
            "plan_id": str(convert_data.plan_id),
            "plan_name": plan.name
        }
    )
    
    logger.info("Admin %s converted user %s to paid (plan: %s)", current_user.email, user.email, plan.name)
    
    return MessageResponse(
        message=f"User {user.email} converted to paid. Assigned plan: {plan.name}"
    )


# ============================================================================
# ISSUE #90: ADMIN BROADCAST NOTIFICATIONS
# ============================================================================

@router.post("/broadcast", response_model=MessageResponse)
async def broadcast_notification(
    broadcast_data: BroadcastRequest,
    current_user: User = Depends(require_superadmin),
    db: AsyncSession = Depends(get_db)
):
    """Broadcast a notification to all users (or filtered by role).
    
    Sends a notification to all users, optionally filtered by role.
    """
    # Build query to get all users (or filtered by role)
    query = select(User).where(User.is_active == True)
    
    if broadcast_data.target_role:
        query = query.where(User.role == broadcast_data.target_role)
    
    result = await db.execute(query)
    users = result.scalars().all()
    
    if not users:
        return MessageResponse(message="No users found matching the criteria")
    
    # Create notification for each user
    count = 0
    for user in users:
        await create_notification(
            db=db,
            user_id=user.id,
            title=broadcast_data.title,
            message=broadcast_data.message,
            notification_type=broadcast_data.type,
        )
        count += 1
    
    # Audit log
    await log_admin_action(
        db=db,
        admin_id=current_user.id,
        action="broadcast_notification",
        target_user_id=None,
        details={
            "title": broadcast_data.title,
            "message": broadcast_data.message,
            "target_role": broadcast_data.target_role,
            "user_count": count
        }
    )
    
    logger.info(
        "Admin %s broadcast notification to %d users (role filter: %s)",
        current_user.email,
        count,
        broadcast_data.target_role or "all",
    )
    
    return MessageResponse(
        message=f"Notification broadcast to {count} users"
    )


# ============================================================================
# ISSUES #92 & #93: API USAGE TRACKING & MARGIN ANALYSIS
# ============================================================================

@router.get("/usage/summary", response_model=UsageSummary)
async def get_usage_summary(
    period: str = Query("all", regex="^(all|day|week|month)$"),
    current_user: User = Depends(require_superadmin),
    db: AsyncSession = Depends(get_db)
):
    """Get platform-wide API usage summary.
    
    Query params:
    - period: Time period (all, day, week, month)
    
    Returns total spend and breakdown by service.
    """
    from app.services.api_usage_service import get_total_cost_by_service, get_total_platform_spend
    
    # Convert async session to sync for the service
    sync_db = db.sync_session
    
    total_spend = get_total_platform_spend(sync_db, period)
    by_service = get_total_cost_by_service(sync_db, period)
    
    return UsageSummary(
        total_spend=total_spend,
        retell_cost=by_service.get("retell", 0),
        twilio_cost=by_service.get("twilio", 0),
        sendgrid_cost=by_service.get("sendgrid", 0)
    )


@router.get("/usage/per-user", response_model=List[UserUsage])
async def get_per_user_usage(
    current_user: User = Depends(require_superadmin),
    db: AsyncSession = Depends(get_db)
):
    """Get per-user cost breakdown.
    
    Returns list of users with their total costs and breakdown by service.
    """
    from app.services.api_usage_service import get_cost_per_user
    
    sync_db = db.sync_session
    cost_data = get_cost_per_user(sync_db)
    
    return [UserUsage(**item) for item in cost_data]


@router.get("/usage/margin", response_model=List[UserMargin])
async def get_margin_analysis(
    current_user: User = Depends(require_superadmin),
    db: AsyncSession = Depends(get_db)
):
    """Get per-user margin analysis (revenue minus costs).
    
    Returns list of users with plan price, costs, margin, and alert flag
    for users whose costs exceed their plan price.
    """
    from app.services.api_usage_service import get_user_margin_analysis
    
    sync_db = db.sync_session
    margin_data = get_user_margin_analysis(sync_db)
    
    return [UserMargin(**item) for item in margin_data]


@router.get("/usage/trends", response_model=UsageTrends)
async def get_usage_trends(
    days: int = Query(30, ge=1, le=365),
    current_user: User = Depends(require_superadmin),
    db: AsyncSession = Depends(get_db)
):
    """Get daily cost trends for charts.
    
    Query params:
    - days: Number of days to look back (1-365, default 30)
    
    Returns daily cost data for the specified period.
    """
    from app.services.api_usage_service import get_cost_trends
    
    sync_db = db.sync_session
    trends = get_cost_trends(sync_db, days)
    
    return UsageTrends(
        days=days,
        trends=[DailyCostTrend(**item) for item in trends]
    )


# ============================================================================
# ISSUE #94: AUDIT LOG
# ============================================================================

@router.get("/audit", response_model=AuditLogList)
async def get_audit_logs(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    action: Optional[str] = None,
    admin_id: Optional[UUID] = None,
    target_user_id: Optional[UUID] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    current_user: User = Depends(require_superadmin),
    db: AsyncSession = Depends(get_db)
):
    """Get audit logs with pagination and filtering.
    
    Query params:
    - limit: max results per page (default 50, max 500)
    - offset: pagination offset
    - action: filter by action type
    - admin_id: filter by admin who performed the action
    - target_user_id: filter by target user
    - start_date: filter logs from this date onwards
    - end_date: filter logs up to this date
    """
    # Build query with filters
    query = select(AdminAuditLog)
    filters = []
    
    if action:
        filters.append(AdminAuditLog.action == action)
    if admin_id:
        filters.append(AdminAuditLog.admin_id == admin_id)
    if target_user_id:
        filters.append(AdminAuditLog.target_user_id == target_user_id)
    if start_date:
        filters.append(AdminAuditLog.created_at >= start_date)
    if end_date:
        filters.append(AdminAuditLog.created_at <= end_date)
    
    if filters:
        query = query.where(and_(*filters))
    
    # Get total count
    count_query = select(func.count(AdminAuditLog.id))
    if filters:
        count_query = count_query.where(and_(*filters))
    
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0
    
    # Get paginated results
    query = query.order_by(desc(AdminAuditLog.created_at)).limit(limit).offset(offset)
    result = await db.execute(query)
    logs = result.scalars().all()
    
    # Enrich with admin and target user emails
    enriched_logs = []
    for log in logs:
        # Fetch admin user
        admin_result = await db.execute(select(User).where(User.id == log.admin_id))
        admin = admin_result.scalar_one_or_none()
        
        # Fetch target user if exists
        target_email = None
        if log.target_user_id:
            target_result = await db.execute(select(User).where(User.id == log.target_user_id))
            target = target_result.scalar_one_or_none()
            if target:
                target_email = target.email
        
        enriched_logs.append(AuditLogEntry(
            id=log.id,
            admin_id=log.admin_id,
            action=log.action,
            target_user_id=log.target_user_id,
            details=log.details,
            created_at=log.created_at,
            admin_email=admin.email if admin else None,
            target_email=target_email,
        ))
    
    return AuditLogList(
        logs=enriched_logs,
        total=total,
        limit=limit,
        offset=offset,
    )


# ============================================================================
# ISSUE #95: USER IMPERSONATION
# ============================================================================

@router.get("/impersonate/{user_id}", response_model=ImpersonationResponse)
async def impersonate_user(
    user_id: UUID,
    current_user: User = Depends(require_superadmin),
    db: AsyncSession = Depends(get_db)
):
    """Impersonate a user and get a temporary JWT.
    
    Returns a JWT token that represents the target user, but includes
    `impersonated_by` claim to track that it's an admin viewing.
    """
    # Fetch target user
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Create impersonation token (valid for 1 hour)
    token_data = {
        "sub": str(user.id),
        "email": user.email,
        "impersonated_by": str(current_user.id),
    }
    access_token = create_access_token(token_data, expires_delta=timedelta(hours=1))
    
    # Log to audit trail
    await log_admin_action(
        db=db,
        admin_id=current_user.id,
        action="user_impersonate",
        target_user_id=user.id,
        details={"impersonated_email": user.email}
    )
    
    logger.warning(
        f"Admin {current_user.email} is impersonating user {user.email}"
    )
    
    return ImpersonationResponse(
        access_token=access_token,
        impersonated_user_id=user.id,
        impersonated_email=user.email,
        expires_in=3600,
    )


# ============================================================================
# ISSUE #96: INTEGRATION HEALTH PAGE
# ============================================================================

@router.get("/health", response_model=HealthCheckResponse)
async def get_integration_health(
    current_user: User = Depends(require_superadmin),
    db: AsyncSession = Depends(get_db)
):
    """Check health status of all integrations.
    
    Returns status for: Database, Retell API, Twilio, Stripe, SendGrid.
    Status values: ok, not_configured, error
    """
    from app.core.config import settings
    
    # Check database
    db_status = IntegrationStatus(status="ok")
    try:
        await db.execute(select(func.count(User.id)))
    except Exception as e:
        db_status = IntegrationStatus(status="error", message=str(e))
    
    # Check Retell API
    retell_status = IntegrationStatus(status="not_configured")
    if settings.RETELL_API_KEY:
        try:
            import httpx
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "https://api.retellai.com/v2/list-agents",
                    headers={"Authorization": f"Bearer {settings.RETELL_API_KEY}"},
                    timeout=5.0
                )
                if response.status_code == 200:
                    retell_status = IntegrationStatus(status="ok")
                else:
                    retell_status = IntegrationStatus(
                        status="error", 
                        message=f"HTTP {response.status_code}"
                    )
        except Exception as e:
            retell_status = IntegrationStatus(status="error", message=str(e))
    
    # Check Twilio
    twilio_status = IntegrationStatus(status="not_configured")
    if settings.TWILIO_ACCOUNT_SID and settings.TWILIO_AUTH_TOKEN:
        try:
            import httpx
            from httpx import BasicAuth
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"https://api.twilio.com/2010-04-01/Accounts/{settings.TWILIO_ACCOUNT_SID}.json",
                    auth=BasicAuth(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN),
                    timeout=5.0
                )
                if response.status_code == 200:
                    twilio_status = IntegrationStatus(status="ok")
                else:
                    twilio_status = IntegrationStatus(
                        status="error", 
                        message=f"HTTP {response.status_code}"
                    )
        except Exception as e:
            twilio_status = IntegrationStatus(status="error", message=str(e))
    
    # Check Stripe
    stripe_status = IntegrationStatus(status="not_configured")
    if settings.STRIPE_API_KEY:
        try:
            import httpx
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "https://api.stripe.com/v1/balance",
                    headers={"Authorization": f"Bearer {settings.STRIPE_API_KEY}"},
                    timeout=5.0
                )
                if response.status_code == 200:
                    stripe_status = IntegrationStatus(status="ok")
                else:
                    stripe_status = IntegrationStatus(
                        status="error", 
                        message=f"HTTP {response.status_code}"
                    )
        except Exception as e:
            stripe_status = IntegrationStatus(status="error", message=str(e))
    
    # Check SendGrid
    sendgrid_status = IntegrationStatus(status="not_configured")
    if settings.SENDGRID_API_KEY:
        try:
            import httpx
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "https://api.sendgrid.com/v3/user/profile",
                    headers={"Authorization": f"Bearer {settings.SENDGRID_API_KEY}"},
                    timeout=5.0
                )
                if response.status_code == 200:
                    sendgrid_status = IntegrationStatus(status="ok")
                else:
                    sendgrid_status = IntegrationStatus(
                        status="error", 
                        message=f"HTTP {response.status_code}"
                    )
        except Exception as e:
            sendgrid_status = IntegrationStatus(status="error", message=str(e))
    
    return HealthCheckResponse(
        db=db_status,
        retell=retell_status,
        twilio=twilio_status,
        stripe=stripe_status,
        sendgrid=sendgrid_status,
    )


# ============================================================================
# ISSUE #97: ONBOARDING COMPLETION TRACKING & ANALYTICS FUNNEL
# ============================================================================

@router.get("/analytics/funnel", response_model=OnboardingFunnelResponse)
async def get_onboarding_funnel(
    current_user: User = Depends(require_superadmin),
    db: AsyncSession = Depends(get_db)
):
    """Get onboarding funnel analytics.
    
    Tracks stages:
    - signed_up: user created
    - email_verified: is_verified=True
    - onboarding_started: business.onboarding_completed is not None
    - personality_set: business.assistant_personality is not None
    - phone_configured: business.twilio_phone_number is not None
    - first_call_received: has at least one call record
    
    Returns counts per stage and drop-off percentages.
    """
    # Stage 1: Signed up (all users)
    signed_up_result = await db.execute(select(func.count(User.id)))
    signed_up = signed_up_result.scalar() or 0
    
    # Stage 2: Email verified
    email_verified_result = await db.execute(
        select(func.count(User.id)).where(User.is_verified == True)
    )
    email_verified = email_verified_result.scalar() or 0
    
    # Stage 3: Onboarding started (has business with onboarding completed or personality set)
    # We'll use: user has a business record
    onboarding_started_result = await db.execute(
        select(func.count(User.id)).join(Business, User.business_id == Business.id)
    )
    onboarding_started = onboarding_started_result.scalar() or 0
    
    # Stage 4: Personality set (business has assistant_personality)
    personality_set_result = await db.execute(
        select(func.count(User.id)).join(Business, User.business_id == Business.id)
        .where(Business.assistant_personality.isnot(None))
    )
    personality_set = personality_set_result.scalar() or 0
    
    # Stage 5: Phone configured (business has twilio_phone_number)
    phone_configured_result = await db.execute(
        select(func.count(User.id)).join(Business, User.business_id == Business.id)
        .where(Business.twilio_phone_number.isnot(None))
    )
    phone_configured = phone_configured_result.scalar() or 0
    
    # Stage 6: First call received (user's business has at least one call)
    first_call_result = await db.execute(
        select(func.count(func.distinct(Call.business_id)))
    )
    first_call_received = first_call_result.scalar() or 0
    
    # Calculate drop-off percentages
    stages = [
        OnboardingStageCount(stage="signed_up", count=signed_up, drop_off_percent=0.0),
        OnboardingStageCount(
            stage="email_verified", 
            count=email_verified, 
            drop_off_percent=round((1 - email_verified / signed_up) * 100, 2) if signed_up > 0 else 0.0
        ),
        OnboardingStageCount(
            stage="onboarding_started", 
            count=onboarding_started, 
            drop_off_percent=round((1 - onboarding_started / email_verified) * 100, 2) if email_verified > 0 else 0.0
        ),
        OnboardingStageCount(
            stage="personality_set", 
            count=personality_set, 
            drop_off_percent=round((1 - personality_set / onboarding_started) * 100, 2) if onboarding_started > 0 else 0.0
        ),
        OnboardingStageCount(
            stage="phone_configured", 
            count=phone_configured, 
            drop_off_percent=round((1 - phone_configured / personality_set) * 100, 2) if personality_set > 0 else 0.0
        ),
        OnboardingStageCount(
            stage="first_call_received", 
            count=first_call_received, 
            drop_off_percent=round((1 - first_call_received / phone_configured) * 100, 2) if phone_configured > 0 else 0.0
        ),
    ]
    
    # Overall completion rate (first_call_received / signed_up)
    overall_completion = (first_call_received / signed_up * 100) if signed_up > 0 else 0.0
    
    return OnboardingFunnelResponse(
        stages=stages,
        total_signups=signed_up,
        overall_completion_rate=round(overall_completion, 2),
    )
