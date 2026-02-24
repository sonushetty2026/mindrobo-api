"""Webhook retry queue service.

Issue #103: Save failed webhook payloads and retry with exponential backoff.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.webhook_retry import WebhookRetry

logger = logging.getLogger(__name__)

# Retry configuration
MAX_RETRY_ATTEMPTS = 3
RETRY_DELAYS = [1, 5, 30]  # minutes: 1min, 5min, 30min


async def save_failed_webhook(
    db: AsyncSession,
    service: str,
    payload: Dict[str, Any],
    error: str
):
    """Save a failed webhook payload to the retry queue.
    
    Args:
        db: Database session
        service: Service name ('retell' or 'twilio')
        payload: Original webhook payload (JSON)
        error: Error message from the failed processing
    """
    retry_entry = WebhookRetry(
        service=service,
        payload=payload,
        attempts=0,
        last_error=error,
        status="pending"
    )
    
    db.add(retry_entry)
    await db.commit()
    await db.refresh(retry_entry)
    
    logger.info(
        "Saved failed webhook to retry queue: service=%s, id=%s, error=%s",
        service,
        retry_entry.id,
        error[:100]
    )
    
    return retry_entry


async def get_pending_retries(db: AsyncSession, limit: int = 50) -> list[WebhookRetry]:
    """Get webhooks that are ready for retry.
    
    Returns webhooks with:
    - status='pending' or 'retrying'
    - attempts < MAX_RETRY_ATTEMPTS
    - next retry time has passed (based on exponential backoff)
    """
    now = datetime.utcnow()
    
    query = select(WebhookRetry).where(
        and_(
            WebhookRetry.status.in_(["pending", "retrying"]),
            WebhookRetry.attempts < MAX_RETRY_ATTEMPTS
        )
    ).order_by(WebhookRetry.created_at).limit(limit)
    
    result = await db.execute(query)
    all_pending = result.scalars().all()
    
    # Filter by retry delay
    ready_for_retry = []
    for retry in all_pending:
        if retry.attempts == 0:
            # First retry - always ready
            ready_for_retry.append(retry)
        else:
            # Calculate when this should be retried based on attempts
            delay_minutes = RETRY_DELAYS[min(retry.attempts - 1, len(RETRY_DELAYS) - 1)]
            next_retry_time = retry.updated_at + timedelta(minutes=delay_minutes)
            
            if now >= next_retry_time:
                ready_for_retry.append(retry)
    
    logger.info(
        "Found %d pending webhooks, %d ready for retry",
        len(all_pending),
        len(ready_for_retry)
    )
    
    return ready_for_retry


async def mark_retry_success(db: AsyncSession, retry_id: str):
    """Mark a webhook retry as successful."""
    result = await db.execute(
        select(WebhookRetry).where(WebhookRetry.id == retry_id)
    )
    retry = result.scalar_one_or_none()
    
    if retry:
        retry.status = "success"
        retry.updated_at = datetime.utcnow()
        await db.commit()
        
        logger.info("Webhook retry successful: id=%s, service=%s", retry_id, retry.service)


async def mark_retry_failed(db: AsyncSession, retry_id: str, error: str):
    """Mark a webhook retry attempt as failed and increment attempts.
    
    If max attempts reached, mark as 'failed' permanently.
    """
    result = await db.execute(
        select(WebhookRetry).where(WebhookRetry.id == retry_id)
    )
    retry = result.scalar_one_or_none()
    
    if retry:
        retry.attempts += 1
        retry.last_error = error
        retry.updated_at = datetime.utcnow()
        
        if retry.attempts >= MAX_RETRY_ATTEMPTS:
            retry.status = "failed"
            logger.error(
                "Webhook retry exhausted (max attempts): id=%s, service=%s, error=%s",
                retry_id,
                retry.service,
                error[:100]
            )
        else:
            retry.status = "retrying"
            next_delay = RETRY_DELAYS[min(retry.attempts, len(RETRY_DELAYS) - 1)]
            logger.warning(
                "Webhook retry failed (attempt %d/%d), will retry in %d min: id=%s, error=%s",
                retry.attempts,
                MAX_RETRY_ATTEMPTS,
                next_delay,
                retry_id,
                error[:100]
            )
        
        await db.commit()


async def process_webhook_retries(db: AsyncSession, processor_func):
    """Background task to process pending webhook retries.
    
    This should be called periodically (e.g., via a cron job or background worker).
    
    Args:
        db: Database session
        processor_func: Async function that processes a webhook payload.
                        Should take (service, payload) and return None on success or raise on error.
    """
    retries = await get_pending_retries(db)
    
    success_count = 0
    fail_count = 0
    
    for retry in retries:
        try:
            # Call the processor function
            await processor_func(retry.service, retry.payload)
            
            # Success
            await mark_retry_success(db, str(retry.id))
            success_count += 1
            
        except Exception as e:
            # Failed
            await mark_retry_failed(db, str(retry.id), str(e))
            fail_count += 1
    
    if retries:
        logger.info(
            "Webhook retry batch complete: %d success, %d failed, %d total",
            success_count,
            fail_count,
            len(retries)
        )
    
    return {
        "processed": len(retries),
        "success": success_count,
        "failed": fail_count
    }
