"""Rate limiting service for API usage tracking.

Issue #100: Trial users limited to 50 API calls per day, paid users unlimited/1000 per day.
"""

import logging
from datetime import datetime, timedelta
from fastapi import HTTPException
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.api_usage_log import APIUsageLog

logger = logging.getLogger(__name__)

# Rate limits per plan type
TRIAL_DAILY_LIMIT = 50
PAID_DAILY_LIMIT = 1000


async def check_api_rate_limit(db: AsyncSession, user: User):
    """Check if user has exceeded their daily API rate limit.
    
    Trial users: 50 calls/day
    Paid users: 1000 calls/day
    
    Raises HTTPException 429 if limit exceeded.
    """
    # Determine the user's limit
    if user.is_trial:
        daily_limit = TRIAL_DAILY_LIMIT
    else:
        daily_limit = PAID_DAILY_LIMIT
    
    # Get today's usage count
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    
    usage_count_query = await db.execute(
        select(func.count(APIUsageLog.id)).where(
            and_(
                APIUsageLog.user_id == user.id,
                APIUsageLog.created_at >= today_start
            )
        )
    )
    
    current_usage = usage_count_query.scalar() or 0
    
    if current_usage >= daily_limit:
        logger.warning(
            "Rate limit exceeded for user %s (is_trial=%s): %d/%d calls today",
            user.email,
            user.is_trial,
            current_usage,
            daily_limit
        )
        
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded. Upgrade your plan for higher limits."
        )
    
    # Log remaining quota for debugging
    remaining = daily_limit - current_usage
    logger.debug(
        "Rate limit check for %s: %d/%d used, %d remaining",
        user.email,
        current_usage,
        daily_limit,
        remaining
    )
    
    return {
        "limit": daily_limit,
        "used": current_usage,
        "remaining": remaining
    }
