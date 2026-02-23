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
)

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
    
    # Growth chart (last 30 days)
    growth_chart = []
    for i in range(29, -1, -1):  # Last 30 days
        day_start = today_start - timedelta(days=i)
        day_end = day_start + timedelta(days=1)
        
        day_signups_result = await db.execute(
            select(func.count(User.id)).where(
                and_(
                    User.created_at >= day_start,
                    User.created_at < day_end
                )
            )
        )
        day_signups = day_signups_result.scalar() or 0
        
        growth_chart.append({
            "date": day_start.strftime("%Y-%m-%d"),
            "count": day_signups
        })
    
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
        growth_chart=growth_chart,
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
@router.patch("/users/{user_id}", response_model=AdminUserOut)
async def update_user(
    user_id: UUID,
    update_data: AdminUserUpdate,
    current_user: User = Depends(require_superadmin),
    db: AsyncSession = Depends(get_db)
):
    """Update user fields (role, is_paused, plan_id).
    
    Admin can modify user roles, pause status, and subscription plan.
    Supports both PUT and PATCH methods.
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
