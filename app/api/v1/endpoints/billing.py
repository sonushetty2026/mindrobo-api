"""Billing endpoints for subscription management.

- GET /api/v1/billing/ → Billing page (HTML)
- GET /api/v1/billing/status → Current plan and billing info
- POST /api/v1/billing/portal → Generate Stripe Customer Portal URL
- GET /api/v1/billing/history → Payment history
"""

import logging
from pathlib import Path
from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, Query, HTTPException
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel

from app.core.database import get_db

router = APIRouter()
logger = logging.getLogger(__name__)

# Load billing template
TEMPLATES_DIR = Path(__file__).parent.parent.parent.parent / "app" / "templates"
BILLING_TEMPLATE_PATH = TEMPLATES_DIR / "billing.html"


def _load_billing_template() -> str:
    """Load the billing HTML template from file."""
    if not BILLING_TEMPLATE_PATH.exists():
        logger.error("Billing template not found at %s", BILLING_TEMPLATE_PATH)
        return "<html><body><h1>Billing template not found</h1></body></html>"
    return BILLING_TEMPLATE_PATH.read_text()


# Pydantic schemas
class BillingStatus(BaseModel):
    has_subscription: bool
    plan_name: Optional[str] = None
    price: Optional[float] = None
    next_billing_date: Optional[datetime] = None
    payment_status: Optional[str] = None  # active, past_due, canceled


class PortalRequest(BaseModel):
    business_id: str


class PortalResponse(BaseModel):
    url: str


class PaymentHistoryItem(BaseModel):
    date: datetime
    amount: float
    status: str  # paid, failed, pending
    invoice_url: Optional[str] = None


@router.get("/", response_class=HTMLResponse)
async def billing_page():
    """Serve the billing HTML page."""
    return _load_billing_template()


@router.get("/status", response_model=BillingStatus)
async def billing_status(
    business_id: str = Query(..., description="Business ID"),
    db: AsyncSession = Depends(get_db)
):
    """Get current billing status for a business.
    
    NOTE: This is a placeholder implementation.
    In production, this should integrate with Stripe API to fetch real subscription data.
    """
    from app.models.business import Business
    
    # Fetch business
    result = await db.execute(select(Business).where(Business.id == int(business_id)))
    business = result.scalar_one_or_none()
    
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
    
    # TODO: Integrate with Stripe to fetch real subscription data
    # For now, return mock data
    
    # Check if business has stripe_customer_id (indicates subscription)
    has_subscription = hasattr(business, 'stripe_customer_id') and business.stripe_customer_id is not None
    
    if has_subscription:
        return BillingStatus(
            has_subscription=True,
            plan_name="MindRobo Pro",
            price=49.0,
            next_billing_date=datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0),
            payment_status="active"
        )
    else:
        return BillingStatus(
            has_subscription=False
        )


@router.post("/portal", response_model=PortalResponse)
async def create_portal_session(
    request: PortalRequest,
    db: AsyncSession = Depends(get_db)
):
    """Generate Stripe Customer Portal session URL.
    
    NOTE: This is a placeholder implementation.
    In production, this should use Stripe API to create a real portal session.
    """
    from app.models.business import Business
    
    # Fetch business
    result = await db.execute(select(Business).where(Business.id == int(request.business_id)))
    business = result.scalar_one_or_none()
    
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
    
    # TODO: Integrate with Stripe
    # For now, return a placeholder URL
    # In production:
    # import stripe
    # session = stripe.billing_portal.Session.create(
    #     customer=business.stripe_customer_id,
    #     return_url=f"{request.url.scheme}://{request.url.netloc}/api/v1/billing/"
    # )
    # return PortalResponse(url=session.url)
    
    logger.warning(
        "Stripe integration not configured. Returning placeholder portal URL for business %s",
        request.business_id
    )
    
    # Return placeholder URL
    return PortalResponse(
        url="https://billing.stripe.com/p/login/test_placeholder"
    )


@router.get("/history", response_model=List[PaymentHistoryItem])
async def payment_history(
    business_id: str = Query(..., description="Business ID"),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    """Get payment history for a business.
    
    NOTE: This is a placeholder implementation.
    In production, this should integrate with Stripe API to fetch real payment history.
    """
    from app.models.business import Business
    
    # Fetch business
    result = await db.execute(select(Business).where(Business.id == int(business_id)))
    business = result.scalar_one_or_none()
    
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
    
    # TODO: Integrate with Stripe to fetch real payment history
    # For now, return empty list or mock data
    
    # Check if business has subscription
    has_subscription = hasattr(business, 'stripe_customer_id') and business.stripe_customer_id is not None
    
    if not has_subscription:
        return []
    
    # Return mock payment history for demo
    return [
        PaymentHistoryItem(
            date=datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0),
            amount=49.0,
            status="paid",
            invoice_url="https://invoice.stripe.com/i/test_placeholder"
        )
    ]
