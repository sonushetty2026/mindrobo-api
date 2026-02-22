"""Stripe billing service for MindRobo subscriptions."""

import logging
import stripe
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import settings
from app.models.business import Business

logger = logging.getLogger(__name__)

# Configure Stripe
stripe.api_key = settings.STRIPE_API_KEY

MONTHLY_PRICE = 4900  # $49.00 in cents


async def create_checkout_session(
    business_id: str,
    success_url: str,
    cancel_url: str,
    db: AsyncSession,
) -> Optional[str]:
    """Create a Stripe checkout session for a business.
    
    Returns the checkout session URL, or None if Stripe is not configured.
    """
    if not settings.STRIPE_API_KEY or not settings.STRIPE_PRICE_ID:
        logger.warning("Stripe not configured — skipping checkout session creation")
        return None
    
    # Fetch the business
    result = await db.execute(select(Business).where(Business.id == business_id))
    business = result.scalar_one_or_none()
    
    if not business:
        logger.error("Business not found: %s", business_id)
        return None
    
    try:
        # Create or retrieve Stripe customer
        if not business.stripe_customer_id:
            customer = stripe.Customer.create(
                email=business.owner_email or "",
                metadata={"business_id": str(business.id)},
            )
            business.stripe_customer_id = customer.id
            await db.commit()
            logger.info("Created Stripe customer %s for business %s", customer.id, business.id)
        
        # Create checkout session
        session = stripe.checkout.Session.create(
            customer=business.stripe_customer_id,
            payment_method_types=["card"],
            line_items=[{
                "price": settings.STRIPE_PRICE_ID,
                "quantity": 1,
            }],
            mode="subscription",
            success_url=success_url,
            cancel_url=cancel_url,
            metadata={"business_id": str(business.id)},
        )
        
        logger.info("Created checkout session %s for business %s", session.id, business.id)
        return session.url
    
    except stripe.error.StripeError as e:
        logger.error("Stripe error creating checkout session: %s", e)
        return None


async def handle_subscription_created(
    subscription_id: str,
    customer_id: str,
    status: str,
    db: AsyncSession,
) -> None:
    """Handle subscription.created webhook from Stripe."""
    result = await db.execute(
        select(Business).where(Business.stripe_customer_id == customer_id)
    )
    business = result.scalar_one_or_none()
    
    if not business:
        logger.warning("Business not found for Stripe customer %s", customer_id)
        return
    
    business.subscription_status = status
    await db.commit()
    
    logger.info(
        "Subscription %s created for business %s — status: %s",
        subscription_id, business.id, status
    )


async def handle_subscription_updated(
    subscription_id: str,
    customer_id: str,
    status: str,
    db: AsyncSession,
) -> None:
    """Handle subscription.updated webhook from Stripe."""
    result = await db.execute(
        select(Business).where(Business.stripe_customer_id == customer_id)
    )
    business = result.scalar_one_or_none()
    
    if not business:
        logger.warning("Business not found for Stripe customer %s", customer_id)
        return
    
    business.subscription_status = status
    await db.commit()
    
    logger.info(
        "Subscription %s updated for business %s — status: %s",
        subscription_id, business.id, status
    )


async def handle_subscription_deleted(
    subscription_id: str,
    customer_id: str,
    db: AsyncSession,
) -> None:
    """Handle subscription.deleted webhook from Stripe."""
    result = await db.execute(
        select(Business).where(Business.stripe_customer_id == customer_id)
    )
    business = result.scalar_one_or_none()
    
    if not business:
        logger.warning("Business not found for Stripe customer %s", customer_id)
        return
    
    business.subscription_status = "canceled"
    await db.commit()
    
    logger.info(
        "Subscription %s canceled for business %s",
        subscription_id, business.id
    )
