"""Trial usage limit checking."""

import logging
from uuid import UUID
from fastapi import HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.call import Call
from app.models.lead import Lead
from app.models.appointment import Appointment

logger = logging.getLogger(__name__)

# Configurable trial limits
TRIAL_LIMITS = {
    "calls": 50,
    "leads": 100,
    "appointments": 50,
}


async def check_trial_limit_calls(db: AsyncSession, business_id: UUID, user: User):
    """Check if trial user has exceeded call creation limit."""
    if not user.is_trial:
        return  # Paid users have no limits
    
    # Count existing calls
    query = select(func.count(Call.id)).where(Call.business_id == business_id)
    result = await db.execute(query)
    count = result.scalar_one()
    
    if count >= TRIAL_LIMITS["calls"]:
        logger.warning(
            "User %s (trial) hit call limit: %d/%d",
            user.email,
            count,
            TRIAL_LIMITS["calls"],
        )
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Trial limit reached: {TRIAL_LIMITS['calls']} calls max. Please upgrade to continue.",
        )


async def check_trial_limit_leads(db: AsyncSession, business_id: UUID, user: User):
    """Check if trial user has exceeded lead creation limit."""
    if not user.is_trial:
        return  # Paid users have no limits
    
    # Count existing leads
    query = select(func.count(Lead.id)).where(Lead.business_id == business_id)
    result = await db.execute(query)
    count = result.scalar_one()
    
    if count >= TRIAL_LIMITS["leads"]:
        logger.warning(
            "User %s (trial) hit lead limit: %d/%d",
            user.email,
            count,
            TRIAL_LIMITS["leads"],
        )
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Trial limit reached: {TRIAL_LIMITS['leads']} leads max. Please upgrade to continue.",
        )


async def check_trial_limit_appointments(db: AsyncSession, business_id: UUID, user: User):
    """Check if trial user has exceeded appointment creation limit."""
    if not user.is_trial:
        return  # Paid users have no limits
    
    # Count existing appointments
    query = select(func.count(Appointment.id)).where(Appointment.business_id == business_id)
    result = await db.execute(query)
    count = result.scalar_one()
    
    if count >= TRIAL_LIMITS["appointments"]:
        logger.warning(
            "User %s (trial) hit appointment limit: %d/%d",
            user.email,
            count,
            TRIAL_LIMITS["appointments"],
        )
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Trial limit reached: {TRIAL_LIMITS['appointments']} appointments max. Please upgrade to continue.",
        )
