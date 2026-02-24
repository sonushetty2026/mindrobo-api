"""Admin-only endpoints for MindRobo API.

All routes require superadmin role.
"""

import logging
from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_

from app.core.database import get_db
from app.core.dependencies import require_superadmin
from app.models.user import User
from app.models.subscription_plan import SubscriptionPlan
from app.models.api_usage_log import APIUsageLog
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
    ServiceBreakdown,
    UserUsage,
    UserMargin,
    DailyCostTrend,
)
from app.schemas.notification import BroadcastRequest
from app.services.notification_service import create_notification
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
# ISSUE #92 & #93: API USAGE TRACKING
# ============================================================================

@router.get("/usage/summary", response_model=UsageSummary)
async def get_usage_summary(
    period: str = Query("month", regex="^(day|week|month)$"),
    current_user: User = Depends(require_superadmin),
    db: AsyncSession = Depends(get_db)
):
    """Get platform-wide API usage summary.
    
    Args:
        period: Time period (day, week, month)
    
    Returns: Total spend and breakdown by service
    """
    now = datetime.utcnow()
    
    if period == "day":
        period_start = datetime(now.year, now.month, now.day)
    elif period == "week":
        period_start = now - timedelta(days=7)
    else:  # month
        period_start = datetime(now.year, now.month, 1)
    
    # Get total cost and service breakdown
    usage_query = await db.execute(
        select(
            APIUsageLog.service,
            func.sum(APIUsageLog.cost_cents).label("total_cost_cents"),
            func.count(APIUsageLog.id).label("call_count")
        )
        .where(APIUsageLog.created_at >= period_start)
        .group_by(APIUsageLog.service)
    )
    
    usage_results = usage_query.all()
    
    service_breakdown = [
        ServiceBreakdown(
            service=row.service,
            total_cost_cents=int(row.total_cost_cents or 0),
            call_count=row.call_count
        )
        for row in usage_results
    ]
    
    total_cost = sum(s.total_cost_cents for s in service_breakdown)
    
    return UsageSummary(
        total_cost_cents=total_cost,
        service_breakdown=service_breakdown,
        period_start=period_start,
        period_end=now
    )


@router.get("/usage/per-user", response_model=list[UserUsage])
async def get_per_user_usage(
    period: str = Query("month", regex="^(day|week|month)$"),
    limit: int = Query(50, ge=1, le=500),
    current_user: User = Depends(require_superadmin),
    db: AsyncSession = Depends(get_db)
):
    """Get per-user API usage breakdown.
    
    Args:
        period: Time period (day, week, month)
        limit: Max number of users to return
    
    Returns: List of users with their usage breakdown
    """
    now = datetime.utcnow()
    
    if period == "day":
        period_start = datetime(now.year, now.month, now.day)
    elif period == "week":
        period_start = now - timedelta(days=7)
    else:  # month
        period_start = datetime(now.year, now.month, 1)
    
    # Get usage by user and service
    usage_query = await db.execute(
        select(
            APIUsageLog.user_id,
            APIUsageLog.service,
            func.sum(APIUsageLog.cost_cents).label("total_cost_cents"),
            func.count(APIUsageLog.id).label("call_count")
        )
        .where(APIUsageLog.created_at >= period_start)
        .group_by(APIUsageLog.user_id, APIUsageLog.service)
        .order_by(func.sum(APIUsageLog.cost_cents).desc())
    )
    
    usage_results = usage_query.all()
    
    # Group by user
    user_usage_map = {}
    for row in usage_results:
        if row.user_id not in user_usage_map:
            user_usage_map[row.user_id] = {
                "services": [],
                "total": 0
            }
        
        cost = int(row.total_cost_cents or 0)
        user_usage_map[row.user_id]["services"].append(
            ServiceBreakdown(
                service=row.service,
                total_cost_cents=cost,
                call_count=row.call_count
            )
        )
        user_usage_map[row.user_id]["total"] += cost
    
    # Get user details
    user_ids = list(user_usage_map.keys())[:limit]
    users_query = await db.execute(
        select(User).where(User.id.in_(user_ids))
    )
    users = {u.id: u for u in users_query.scalars().all()}
    
    result = []
    for user_id in sorted(user_ids, key=lambda uid: user_usage_map[uid]["total"], reverse=True):
        user = users.get(user_id)
        if user:
            result.append(UserUsage(
                user_id=user.id,
                email=user.email,
                full_name=user.full_name,
                total_cost_cents=user_usage_map[user_id]["total"],
                service_breakdown=user_usage_map[user_id]["services"]
            ))
    
    return result[:limit]


@router.get("/usage/margin", response_model=list[UserMargin])
async def get_user_margin(
    period: str = Query("month", regex="^(day|week|month)$"),
    current_user: User = Depends(require_superadmin),
    db: AsyncSession = Depends(get_db)
):
    """Get per-user margin analysis (plan price vs. API costs).
    
    Flags users whose monthly cost exceeds their plan price.
    
    Args:
        period: Time period (currently always month for plan pricing)
    
    Returns: List of users with margin calculations
    """
    now = datetime.utcnow()
    month_start = datetime(now.year, now.month, 1)
    
    # Get usage by user for current month
    usage_query = await db.execute(
        select(
            APIUsageLog.user_id,
            func.sum(APIUsageLog.cost_cents).label("total_cost_cents")
        )
        .where(APIUsageLog.created_at >= month_start)
        .group_by(APIUsageLog.user_id)
    )
    
    usage_results = {row.user_id: int(row.total_cost_cents or 0) for row in usage_query.all()}
    
    # Get users with their plans
    users_query = await db.execute(
        select(User, SubscriptionPlan)
        .outerjoin(SubscriptionPlan, User.plan_id == SubscriptionPlan.id)
        .where(User.id.in_(list(usage_results.keys())))
    )
    
    result = []
    for user, plan in users_query.all():
        total_cost = usage_results.get(user.id, 0)
        plan_price = plan.price_cents if plan else 0
        margin = plan_price - total_cost
        margin_pct = (margin / plan_price * 100) if plan_price > 0 else 0
        
        result.append(UserMargin(
            user_id=user.id,
            email=user.email,
            full_name=user.full_name,
            plan_price_cents=plan_price,
            total_cost_cents=total_cost,
            margin_cents=margin,
            margin_percentage=round(margin_pct, 2),
            is_profitable=margin >= 0,
            period_start=month_start,
            period_end=now
        ))
    
    # Sort by margin (least profitable first)
    result.sort(key=lambda x: x.margin_cents)
    
    return result


@router.get("/usage/trends", response_model=list[DailyCostTrend])
async def get_usage_trends(
    days: int = Query(30, ge=1, le=90),
    current_user: User = Depends(require_superadmin),
    db: AsyncSession = Depends(get_db)
):
    """Get daily cost trends for charts (last N days).
    
    Args:
        days: Number of days to include (max 90)
    
    Returns: Daily cost data broken down by service
    """
    now = datetime.utcnow()
    start_date = now - timedelta(days=days)
    
    # Get daily usage by service
    usage_query = await db.execute(
        select(
            func.date(APIUsageLog.created_at).label("date"),
            APIUsageLog.service,
            func.sum(APIUsageLog.cost_cents).label("total_cost_cents")
        )
        .where(APIUsageLog.created_at >= start_date)
        .group_by(func.date(APIUsageLog.created_at), APIUsageLog.service)
        .order_by(func.date(APIUsageLog.created_at))
    )
    
    usage_results = usage_query.all()
    
    # Build a map of date -> {service -> cost}
    daily_map = {}
    for row in usage_results:
        date_str = row.date.strftime("%Y-%m-%d")
        if date_str not in daily_map:
            daily_map[date_str] = {
                "total": 0,
                "retell": 0,
                "twilio": 0,
                "sendgrid": 0
            }
        
        cost = int(row.total_cost_cents or 0)
        daily_map[date_str]["total"] += cost
        daily_map[date_str][row.service] = cost
    
    # Generate list for all days (fill zeros for missing days)
    result = []
    current = start_date.date()
    end = now.date()
    
    while current <= end:
        date_str = current.strftime("%Y-%m-%d")
        data = daily_map.get(date_str, {"total": 0, "retell": 0, "twilio": 0, "sendgrid": 0})
        
        result.append(DailyCostTrend(
            date=date_str,
            total_cost_cents=data["total"],
            retell_cost_cents=data.get("retell", 0),
            twilio_cost_cents=data.get("twilio", 0),
            sendgrid_cost_cents=data.get("sendgrid", 0)
        ))
        
        current += timedelta(days=1)
    
    return result
