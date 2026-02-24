"""API usage tracking utilities.

Logs usage to api_usage_logs table for cost tracking and margin analysis.
"""

import logging
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.api_usage_log import APIUsageLog

logger = logging.getLogger(__name__)


async def log_api_usage(
    db: AsyncSession,
    user_id: UUID,
    service: str,
    endpoint: str,
    cost_cents: int,
    request_data: dict | None = None,
) -> None:
    """
    Log an API usage event.
    
    Args:
        db: Database session
        user_id: User who triggered the API call
        service: Service name (retell, twilio, sendgrid)
        endpoint: Specific endpoint/action (e.g., "call", "sms", "email")
        cost_cents: Cost in cents (e.g., 10 = $0.10)
        request_data: Optional metadata about the request
    """
    try:
        log_entry = APIUsageLog(
            user_id=user_id,
            service=service,
            endpoint=endpoint,
            cost_cents=cost_cents,
            request_data=request_data,
        )
        db.add(log_entry)
        await db.commit()
        logger.info(
            f"API usage logged: user={user_id} service={service} "
            f"endpoint={endpoint} cost={cost_cents}¢"
        )
    except Exception as e:
        logger.error(f"Failed to log API usage: {e}")
        # Don't raise — usage logging should never break the main flow
        await db.rollback()
