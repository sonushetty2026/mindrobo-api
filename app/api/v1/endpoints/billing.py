"""Billing and subscription endpoints for MindRobo."""

import logging
import stripe
from fastapi import APIRouter, Request, HTTPException, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.config import settings
from app.models.user import User
from app.services.billing import (
    create_checkout_session,
    handle_subscription_created,
    handle_subscription_updated,
    handle_subscription_deleted,
)

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/create-checkout")
async def create_checkout(
    success_url: str = Query(..., description="URL to redirect on success"),
    cancel_url: str = Query(..., description="URL to redirect on cancel"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a Stripe checkout session for the authenticated user's business.
    
    Returns a checkout URL to redirect the user to.
    """
    if not settings.STRIPE_API_KEY:
        raise HTTPException(
            status_code=503,
            detail="Billing is not configured — please contact support"
        )
    
    checkout_url = await create_checkout_session(
        business_id=str(current_user.business_id),
        success_url=success_url,
        cancel_url=cancel_url,
        db=db,
    )
    
    if not checkout_url:
        raise HTTPException(
            status_code=500,
            detail="Failed to create checkout session"
        )
    
    return {"checkout_url": checkout_url}


@router.post("/webhook")
async def stripe_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    """Handle Stripe webhook events.
    
    Stripe sends webhooks for subscription events (created, updated, deleted).
    """
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")
    
    if not settings.STRIPE_WEBHOOK_SECRET:
        logger.warning("Stripe webhook secret not configured — skipping verification")
        event_dict = await request.json()
        event = stripe.Event.construct_from(event_dict, stripe.api_key)
    else:
        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
            )
        except ValueError:
            logger.error("Invalid webhook payload")
            raise HTTPException(status_code=400, detail="Invalid payload")
        except stripe.error.SignatureVerificationError:
            logger.error("Invalid webhook signature")
            raise HTTPException(status_code=400, detail="Invalid signature")
    
    event_type = event["type"]
    data = event["data"]["object"]
    
    logger.info("Stripe webhook received: %s", event_type)
    
    if event_type == "customer.subscription.created":
        await handle_subscription_created(
            subscription_id=data["id"],
            customer_id=data["customer"],
            status=data["status"],
            db=db,
        )
    
    elif event_type == "customer.subscription.updated":
        await handle_subscription_updated(
            subscription_id=data["id"],
            customer_id=data["customer"],
            status=data["status"],
            db=db,
        )
    
    elif event_type == "customer.subscription.deleted":
        await handle_subscription_deleted(
            subscription_id=data["id"],
            customer_id=data["customer"],
            db=db,
        )
    
    else:
        logger.info("Unhandled Stripe event type: %s", event_type)
    
    return {"status": "ok"}
