"""User-related endpoints for MindRobo."""

import logging
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user, check_trial_status
from app.models.user import User
from app.models.call import Call
from app.models.lead import Lead
from app.models.appointment import Appointment
from app.schemas.notification import (
    TrialStatusResponse,
    UsageLimitsResponse,
    FCMTokenRequest,
)
from app.schemas.auth import MessageResponse

router = APIRouter()
logger = logging.getLogger(__name__)

# Configurable trial limits
TRIAL_LIMITS = {
    "calls": 50,
    "leads": 100,
    "appointments": 50,
}


@router.get("/me/trial-status", response_model=TrialStatusResponse)
async def get_trial_status(
    current_user: User = Depends(get_current_user),
):
    """Get trial status for current user.
    
    Returns trial info, days remaining, pause status, and grace period flag.
    """
    if not current_user.is_trial:
        return TrialStatusResponse(
            is_trial=False,
            trial_ends_at=None,
            days_remaining=None,
            is_paused=current_user.is_paused,
            in_grace_period=False,
        )
    
    if not current_user.trial_ends_at:
        return TrialStatusResponse(
            is_trial=True,
            trial_ends_at=None,
            days_remaining=None,
            is_paused=current_user.is_paused,
            in_grace_period=False,
        )
    
    now = datetime.utcnow()
    trial_ends_at = current_user.trial_ends_at
    grace_period_end = trial_ends_at + timedelta(days=3)
    
    # Calculate days remaining until trial ends (not grace period)
    if now < trial_ends_at:
        days_remaining = (trial_ends_at - now).days
        in_grace_period = False
    elif now < grace_period_end:
        # In grace period
        days_remaining = 0
        in_grace_period = True
    else:
        # Grace period expired
        days_remaining = 0
        in_grace_period = False
    
    return TrialStatusResponse(
        is_trial=True,
        trial_ends_at=trial_ends_at,
        days_remaining=days_remaining,
        is_paused=current_user.is_paused,
        in_grace_period=in_grace_period,
    )


@router.get("/me/usage-limits", response_model=UsageLimitsResponse)
async def get_usage_limits(
    current_user: User = Depends(check_trial_status),
    db: AsyncSession = Depends(get_db),
):
    """Get current usage vs limits for trial users.
    
    Protected by trial check.
    """
    # Count calls
    calls_query = select(func.count(Call.id)).where(
        Call.business_id == current_user.business_id
    )
    calls_result = await db.execute(calls_query)
    calls_used = calls_result.scalar_one()
    
    # Count leads
    leads_query = select(func.count(Lead.id)).where(
        Lead.business_id == current_user.business_id
    )
    leads_result = await db.execute(leads_query)
    leads_used = leads_result.scalar_one()
    
    # Count appointments
    appointments_query = select(func.count(Appointment.id)).where(
        Appointment.business_id == current_user.business_id
    )
    appointments_result = await db.execute(appointments_query)
    appointments_used = appointments_result.scalar_one()
    
    return UsageLimitsResponse(
        calls_used=calls_used,
        calls_limit=TRIAL_LIMITS["calls"],
        leads_used=leads_used,
        leads_limit=TRIAL_LIMITS["leads"],
        appointments_used=appointments_used,
        appointments_limit=TRIAL_LIMITS["appointments"],
        is_trial=current_user.is_trial,
    )


@router.post("/me/fcm-token", response_model=MessageResponse)
async def register_fcm_token(
    token_data: FCMTokenRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Register FCM token for push notifications.
    
    Stub: saves token to user record, actual FCM sending is logged only.
    """
    current_user.fcm_token = token_data.fcm_token
    await db.commit()
    
    logger.info(
        "FCM token registered for user %s: %s...",
        current_user.email,
        token_data.fcm_token[:20],
    )
    
    return MessageResponse(message="FCM token registered successfully")
