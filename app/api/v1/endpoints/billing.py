"""Billing and subscription endpoints for MindRobo."""

import logging
import stripe
import os
from uuid import UUID
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel
from fastapi import APIRouter, Request, HTTPException, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.config import settings
from app.models.business import Business
from app.services.billing import (
    create_checkout_session,
    handle_subscription_created,
    handle_subscription_updated,
    handle_subscription_deleted,
)

router = APIRouter()
logger = logging.getLogger(__name__)


# Response models
class BillingStatusOut(BaseModel):
    """Billing status response."""
    plan: str
    status: str
    next_billing_date: Optional[str] = None
    amount: Optional[float] = None


class BillingPortalOut(BaseModel):
    """Billing portal response."""
    url: str


class PaymentHistoryItem(BaseModel):
    """Payment history item."""
    date: str
    amount: float
    status: str
    invoice_url: Optional[str] = None


@router.post("/create-checkout")
async def create_checkout(
    business_id: str = Query(..., description="Business ID for subscription"),
    success_url: str = Query(..., description="URL to redirect on success"),
    cancel_url: str = Query(..., description="URL to redirect on cancel"),
    db: AsyncSession = Depends(get_db),
):
    """Create a Stripe checkout session for a business.
    
    Returns a checkout URL to redirect the user to.
    
    NOTE: Once auth is merged, this endpoint should require authentication
    and use current_user.business_id instead of accepting business_id as param.
    """
    if not settings.STRIPE_API_KEY:
        raise HTTPException(
            status_code=503,
            detail="Billing is not configured — please contact support"
        )
    
    checkout_url = await create_checkout_session(
        business_id=business_id,
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


@router.get("/status", response_model=BillingStatusOut)
async def get_billing_status(
    business_id: UUID = Query(..., description="Business ID"),
    db: AsyncSession = Depends(get_db),
):
    """Get current billing status for a business."""
    # Fetch business
    result = await db.execute(select(Business).where(Business.id == business_id))
    business = result.scalar_one_or_none()
    
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
    
    # If Stripe not configured, return default
    if not os.getenv("STRIPE_SECRET_KEY"):
        return BillingStatusOut(
            plan="free",
            status="active",
            next_billing_date=None,
            amount=None,
        )
    
    # Initialize Stripe
    stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
    
    # If no Stripe customer, return trial/free
    if not business.stripe_customer_id:
        return BillingStatusOut(
            plan="trial" if business.subscription_status == "trial" else "free",
            status=business.subscription_status or "active",
            next_billing_date=None,
            amount=None,
        )
    
    try:
        # Fetch subscription from Stripe
        subscriptions = stripe.Subscription.list(
            customer=business.stripe_customer_id,
            status="active",
            limit=1,
        )
        
        if not subscriptions.data:
            return BillingStatusOut(
                plan="free",
                status="canceled",
                next_billing_date=None,
                amount=None,
            )
        
        subscription = subscriptions.data[0]
        next_billing = datetime.fromtimestamp(subscription.current_period_end).strftime("%Y-%m-%d")
        amount = subscription.plan.amount / 100  # Convert cents to dollars
        
        return BillingStatusOut(
            plan=subscription.plan.nickname or "pro",
            status=subscription.status,
            next_billing_date=next_billing,
            amount=amount,
        )
    
    except Exception as e:
        logger.error(f"Error fetching billing status: {e}")
        return BillingStatusOut(
            plan="unknown",
            status="error",
            next_billing_date=None,
            amount=None,
        )


@router.post("/portal", response_model=BillingPortalOut)
async def create_billing_portal(
    business_id: UUID = Query(..., description="Business ID"),
    return_url: str = Query(..., description="URL to return to after portal session"),
    db: AsyncSession = Depends(get_db),
):
    """Create a Stripe Customer Portal session."""
    # Fetch business
    result = await db.execute(select(Business).where(Business.id == business_id))
    business = result.scalar_one_or_none()
    
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
    
    # Check Stripe configuration
    if not os.getenv("STRIPE_SECRET_KEY"):
        raise HTTPException(
            status_code=503,
            detail="Billing portal is not configured — please contact support"
        )
    
    # Check if business has Stripe customer
    if not business.stripe_customer_id:
        raise HTTPException(
            status_code=400,
            detail="No billing account found — please subscribe first"
        )
    
    # Initialize Stripe
    stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
    
    try:
        # Create portal session
        portal_session = stripe.billing_portal.Session.create(
            customer=business.stripe_customer_id,
            return_url=return_url,
        )
        
        return BillingPortalOut(url=portal_session.url)
    
    except Exception as e:
        logger.error(f"Error creating portal session: {e}")
        raise HTTPException(status_code=500, detail="Failed to create portal session")


@router.get("/history", response_model=List[PaymentHistoryItem])
async def get_payment_history(
    business_id: UUID = Query(..., description="Business ID"),
    limit: int = Query(10, le=100),
    db: AsyncSession = Depends(get_db),
):
    """Get payment history for a business."""
    # Fetch business
    result = await db.execute(select(Business).where(Business.id == business_id))
    business = result.scalar_one_or_none()
    
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
    
    # If Stripe not configured or no customer, return empty
    if not os.getenv("STRIPE_SECRET_KEY") or not business.stripe_customer_id:
        return []
    
    # Initialize Stripe
    stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
    
    try:
        # Fetch invoices from Stripe
        invoices = stripe.Invoice.list(
            customer=business.stripe_customer_id,
            limit=limit,
        )
        
        history = []
        for invoice in invoices.data:
            history.append(PaymentHistoryItem(
                date=datetime.fromtimestamp(invoice.created).strftime("%Y-%m-%d"),
                amount=invoice.amount_paid / 100,  # Convert cents to dollars
                status=invoice.status,
                invoice_url=invoice.hosted_invoice_url,
            ))
        
        return history
    
    except Exception as e:
        logger.error(f"Error fetching payment history: {e}")
        return []
