"""Business onboarding and agent configuration endpoints."""

import logging
from pathlib import Path
from uuid import UUID
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.deps import get_current_user_optional
from app.models.business import Business
from app.models.user import User
from app.schemas.onboarding import (
    BusinessOnboardingRequest,
    AgentConfigRequest,
    AgentConfigResponse,
    TestCallResponse,
    FAQ
)

router = APIRouter()
logger = logging.getLogger(__name__)

# Load onboarding template
TEMPLATES_DIR = Path(__file__).parent.parent.parent.parent / "app" / "templates"
ONBOARDING_TEMPLATE_PATH = TEMPLATES_DIR / "onboarding.html"


def _load_onboarding_template() -> str:
    """Load the onboarding HTML template from file."""
    if not ONBOARDING_TEMPLATE_PATH.exists():
        logger.error("Onboarding template not found at %s", ONBOARDING_TEMPLATE_PATH)
        return "<html><body><h1>Onboarding template not found</h1></body></html>"
    return ONBOARDING_TEMPLATE_PATH.read_text()


@router.get("/", response_class=HTMLResponse)
async def onboarding_page():
    """Serve the onboarding wizard HTML page."""
    return _load_onboarding_template()


@router.post("/onboard", status_code=201)
async def onboard_business(
    data: BusinessOnboardingRequest,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """Full business onboarding endpoint.
    
    Creates a new business with agent configuration.
    """
    # Create business
    business = Business(
        name=data.business_name,
        owner_phone=data.owner_phone,
        industry=data.industry,
        hours_of_operation=data.hours_of_operation,
        greeting_script=data.greeting_script,
        faqs=[faq.model_dump() for faq in data.faqs] if data.faqs else [],
        is_active=True,
    )
    
    db.add(business)
    await db.commit()
    await db.refresh(business)
    
    logger.info("Business onboarded: %s (id=%s)", business.name, business.id)
    
    return {
        "business_id": str(business.id),
        "business_name": business.name,
        "message": "Business onboarded successfully",
        "agent_config_url": f"/api/v1/onboarding/{business.id}/config"
    }


@router.get("/{business_id}/config", response_model=AgentConfigResponse)
async def get_agent_config(
    business_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """Get the full agent config for a business."""
    try:
        business_uuid = UUID(business_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid business ID format")
    
    result = await db.execute(select(Business).where(Business.id == business_uuid))
    business = result.scalar_one_or_none()
    
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
    
    return {
        "business_id": str(business.id),
        "business_name": business.name,
        "industry": business.industry,
        "hours_of_operation": business.hours_of_operation,
        "greeting_script": business.greeting_script,
        "faqs": business.faqs,
    }


@router.put("/{business_id}/config")
async def update_agent_config(
    business_id: str,
    updates: AgentConfigRequest,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """Update agent config (greeting, FAQs, hours)."""
    try:
        business_uuid = UUID(business_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid business ID format")
    
    result = await db.execute(select(Business).where(Business.id == business_uuid))
    business = result.scalar_one_or_none()
    
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
    
    # Update fields
    if updates.greeting_script is not None:
        business.greeting_script = updates.greeting_script
    
    if updates.faqs is not None:
        business.faqs = [faq.model_dump() for faq in updates.faqs]
    
    if updates.hours_of_operation is not None:
        business.hours_of_operation = updates.hours_of_operation
    
    if updates.industry is not None:
        business.industry = updates.industry
    
    await db.commit()
    await db.refresh(business)
    
    logger.info("Agent config updated for business %s", business.id)
    
    return {
        "business_id": str(business.id),
        "message": "Config updated successfully",
        "updated_fields": updates.model_dump(exclude_none=True)
    }


@router.post("/{business_id}/test-call", response_model=TestCallResponse)
async def test_call_simulation(
    business_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """Simulate an inbound call and return what the AI would say."""
    try:
        business_uuid = UUID(business_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid business ID format")
    
    result = await db.execute(select(Business).where(Business.id == business_uuid))
    business = result.scalar_one_or_none()
    
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
    
    # Generate greeting
    if business.greeting_script:
        greeting = business.greeting_script
    else:
        greeting = f"Thank you for calling {business.name}. How can I help you today?"
    
    # Format hours
    hours_text = None
    if business.hours_of_operation:
        hours_text = ", ".join([f"{day.title()}: {hours}" for day, hours in business.hours_of_operation.items()])
    
    # Sample FAQs
    sample_faqs = None
    if business.faqs and len(business.faqs) > 0:
        sample_faqs = [faq.get("question", "") for faq in business.faqs[:3]]
    
    return {
        "greeting": greeting,
        "business_name": business.name,
        "hours": hours_text,
        "sample_faqs": sample_faqs,
    }


@router.get("/progress")
async def get_onboarding_progress(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_optional)
):
    """Get current user's onboarding progress."""
    if not current_user or not current_user.business_id:
        return {"step": 0, "completed": False}
    
    result = await db.execute(select(Business).where(Business.id == current_user.business_id))
    business = result.scalar_one_or_none()
    
    if not business:
        return {"step": 0, "completed": False}
    
    return {
        "step": business.onboarding_step or 0,
        "completed": business.onboarding_completed_at is not None,
        "business_id": str(business.id),
        "business_name": business.name,
    }


@router.put("/progress/{step}")
async def save_onboarding_progress(
    step: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_optional)
):
    """Save onboarding step progress (1-4). Step 4 = complete."""
    if not current_user or not current_user.business_id:
        raise HTTPException(status_code=400, detail="No business associated with user")
    
    if step < 0 or step > 4:
        raise HTTPException(status_code=400, detail="Step must be 0-4")
    
    result = await db.execute(select(Business).where(Business.id == current_user.business_id))
    business = result.scalar_one_or_none()
    
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
    
    business.onboarding_step = step
    if step >= 4:
        from datetime import datetime
        business.onboarding_completed_at = datetime.utcnow()
    
    await db.commit()
    
    logger.info("Onboarding progress saved: business=%s step=%d", business.id, step)
    
    return {"step": step, "completed": step >= 4, "message": "Progress saved"}
