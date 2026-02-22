"""Stripe billing endpoints - checkout and webhooks."""

import logging
import stripe
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.config import settings
from app.models.business import Business

router = APIRouter()
logger = logging.getLogger(__name__)

# Configure Stripe
stripe.api_key = getattr(settings, 'STRIPE_SECRET_KEY', 'sk_test_placeholder')
STRIPE_WEBHOOK_SECRET = getattr(settings, 'STRIPE_WEBHOOK_SECRET', '')
PRICE_ID = getattr(settings, 'STRIPE_PRICE_ID', 'price_test_placeholder')  # $49/mo price


@router.post("/create-checkout")
async def create_checkout_session(
    business_id: str,
    success_url: str,
    cancel_url: str,
    db: AsyncSession = Depends(get_db)
):
    """Create a Stripe checkout session for $49/month subscription."""
    
    # Fetch business
    result = await db.execute(select(Business).where(Business.id == business_id))
    business = result.scalar_one_or_none()
    
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
    
    try:
        # Create or retrieve Stripe customer
        if business.stripe_customer_id:
            customer_id = business.stripe_customer_id
        else:
            customer = stripe.Customer.create(
                email=business.owner_email,
                name=business.owner_name or business.name,
                phone=business.owner_phone,
                metadata={"business_id": str(business.id)}
            )
            business.stripe_customer_id = customer.id
            await db.commit()
            customer_id = customer.id
        
        # Create checkout session
        checkout_session = stripe.checkout.Session.create(
            customer=customer_id,
            payment_method_types=['card'],
            line_items=[{
                'price': PRICE_ID,
                'quantity': 1,
            }],
            mode='subscription',
            success_url=success_url,
            cancel_url=cancel_url,
            metadata={"business_id": str(business.id)}
        )
        
        logger.info("Checkout session created: %s for business %s", checkout_session.id, business.id)
        return {"checkout_url": checkout_session.url, "session_id": checkout_session.id}
    
    except stripe.error.StripeError as e:
        logger.error("Stripe error creating checkout: %s", e)
        raise HTTPException(status_code=500, detail=f"Stripe error: {str(e)}")


@router.post("/webhook")
async def stripe_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    """Handle Stripe webhook events (subscription updates)."""
    
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")
    
    try:
        if STRIPE_WEBHOOK_SECRET:
            event = stripe.Webhook.construct_event(
                payload, sig_header, STRIPE_WEBHOOK_SECRET
            )
        else:
            # In test mode without webhook secret
            import json
            event = json.loads(payload)
    except (ValueError, stripe.error.SignatureVerificationError) as e:
        logger.error("Webhook signature verification failed: %s", e)
        raise HTTPException(status_code=400, detail="Invalid signature")
    
    event_type = event['type']
    data_object = event['data']['object']
    
    logger.info("Stripe webhook received: %s", event_type)
    
    # Handle subscription created
    if event_type == 'checkout.session.completed':
        business_id = data_object.get('metadata', {}).get('business_id')
        if business_id:
            result = await db.execute(select(Business).where(Business.id == business_id))
            business = result.scalar_one_or_none()
            if business:
                business.subscription_status = "active"
                await db.commit()
                logger.info("Business %s subscription activated", business_id)
    
    # Handle subscription updated
    elif event_type == 'customer.subscription.updated':
        customer_id = data_object['customer']
        subscription_status = data_object['status']
        
        result = await db.execute(
            select(Business).where(Business.stripe_customer_id == customer_id)
        )
        business = result.scalar_one_or_none()
        
        if business:
            # Map Stripe status to our enum
            status_map = {
                'active': 'active',
                'trialing': 'trialing',
                'past_due': 'past_due',
                'canceled': 'canceled',
                'unpaid': 'inactive',
                'incomplete': 'inactive',
            }
            business.subscription_status = status_map.get(subscription_status, 'inactive')
            await db.commit()
            logger.info("Business %s subscription updated to %s", business.id, subscription_status)
    
    # Handle subscription deleted
    elif event_type == 'customer.subscription.deleted':
        customer_id = data_object['customer']
        result = await db.execute(
            select(Business).where(Business.stripe_customer_id == customer_id)
        )
        business = result.scalar_one_or_none()
        
        if business:
            business.subscription_status = "canceled"
            await db.commit()
            logger.info("Business %s subscription canceled", business.id)
    
    return {"status": "ok"}
