"""Business CRUD endpoints — onboard and manage businesses."""

from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.core.deps import get_current_user, get_current_user_optional
from app.models.business import Business, LeadHandlingPreference
from app.models.user import User
from app.schemas.business import (
    BusinessCreate, 
    BusinessOut, 
    BusinessUpdate,
    PersonalityConfig,
    PersonalityOut,
    CallSettingsConfig,
    CallSettingsOut,
)
from app.services.business_extractor import generate_placeholder_text

router = APIRouter()


def generate_system_prompt(
    business_name: str,
    business_description: str,
    services_and_prices: str,
    owner_name: str | None,
    lead_handling_preference: LeadHandlingPreference,
) -> tuple[str, str]:
    """Generate custom greeting and system prompt from personality config.
    
    Returns:
        (custom_greeting, system_prompt)
    """
    # Generate custom greeting
    custom_greeting = (
        f"Thank you for calling {business_name}! "
        f"I'm your AI assistant here to help you. How can I assist you today?"
    )
    
    # Generate lead handling instruction
    lead_instructions = {
        LeadHandlingPreference.BOOK_APPOINTMENT: 
            "offer to schedule an appointment at a convenient time",
        LeadHandlingPreference.SEND_SMS: 
            "offer to send them a text message with more details and follow up",
        LeadHandlingPreference.TAKE_MESSAGE: 
            "take a detailed message and let them know the owner will call back soon",
    }
    lead_handling_text = lead_instructions.get(
        lead_handling_preference,
        "help them with their inquiry"
    )
    
    # Build system prompt
    owner_text = f"The owner's name is {owner_name}. " if owner_name else ""
    
    system_prompt = (
        f"You are an AI receptionist for {business_name}. "
        f"{business_description} "
        f"Services offered: {services_and_prices}. "
        f"{owner_text}"
        f"When a caller needs help, {lead_handling_text}. "
        f"Always be friendly, professional, and helpful. "
        f"Speak naturally and conversationally."
    )
    
    return custom_greeting, system_prompt


# Legacy endpoints (backward compatibility, optional auth)
@router.post("/", response_model=BusinessOut, status_code=201)
async def create_business(
    biz: BusinessCreate, 
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    """Onboard a new business.
    
    Legacy endpoint - kept for backward compatibility.
    """
    business = Business(**biz.model_dump())
    db.add(business)
    await db.commit()
    await db.refresh(business)
    return business


@router.get("/", response_model=list[BusinessOut])
async def list_businesses(
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    """List businesses.
    
    If authenticated, returns only the user's business.
    If unauthenticated (legacy mode), returns all active businesses.
    """
    if current_user:
        # Authenticated: return only user's business
        result = await db.execute(
            select(Business).where(Business.id == current_user.business_id)
        )
        businesses = [result.scalar_one_or_none()]
        return [b for b in businesses if b]
    else:
        # Unauthenticated: return all (backward compatibility)
        result = await db.execute(
            select(Business)
            .where(Business.is_active == True)
            .order_by(Business.created_at.desc())
        )
        return result.scalars().all()


@router.get("/{business_id}", response_model=BusinessOut)
async def get_business(
    business_id: str, 
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    """Get a business by ID.
    
    If authenticated, only allows access to user's own business.
    If unauthenticated (legacy mode), allows any business.
    """
    try:
        business_uuid = UUID(business_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid business ID format")
    
    result = await db.execute(select(Business).where(Business.id == business_uuid))
    biz = result.scalar_one_or_none()
    
    if not biz:
        raise HTTPException(status_code=404, detail="Business not found")
    
    # If authenticated, verify user owns this business
    if current_user and biz.id != current_user.business_id:
        raise HTTPException(status_code=404, detail="Business not found")
    
    return biz


# Authenticated endpoints
@router.get("/me", response_model=BusinessOut)
async def get_my_business(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get the authenticated user's business."""
    result = await db.execute(select(Business).where(Business.id == current_user.business_id))
    business = result.scalar_one_or_none()
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
    return business


@router.patch("/me", response_model=BusinessOut)
async def update_my_business(
    updates: BusinessUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update the authenticated user's business settings."""
    result = await db.execute(select(Business).where(Business.id == current_user.business_id))
    business = result.scalar_one_or_none()
    
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
    
    # Update fields
    for field, value in updates.model_dump(exclude_unset=True).items():
        setattr(business, field, value)
    
    await db.commit()
    await db.refresh(business)
    return business


# Personality endpoints (Issue #59)
@router.put("/{business_id}/personality", response_model=PersonalityOut)
async def save_personality(
    business_id: UUID,
    personality: PersonalityConfig,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Save agent personality configuration and auto-generate prompts.
    
    Generates custom_greeting and system_prompt from the personality fields.
    """
    # Verify user owns this business
    if current_user.business_id != business_id:
        raise HTTPException(status_code=404, detail="Business not found")
    
    result = await db.execute(select(Business).where(Business.id == business_id))
    business = result.scalar_one_or_none()
    
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
    
    # Update personality fields
    business.business_description = personality.business_description
    business.services_and_prices = personality.services_and_prices
    business.lead_handling_preference = personality.lead_handling_preference
    
    # Update owner_name if provided
    if personality.owner_name:
        business.owner_name = personality.owner_name
    
    # Generate custom greeting and system prompt
    custom_greeting, system_prompt = generate_system_prompt(
        business_name=business.name,
        business_description=personality.business_description,
        services_and_prices=personality.services_and_prices,
        owner_name=personality.owner_name or business.owner_name,
        lead_handling_preference=personality.lead_handling_preference,
    )
    
    business.custom_greeting = custom_greeting
    business.system_prompt = system_prompt
    
    await db.commit()
    await db.refresh(business)
    
    return PersonalityOut(
        business_description=business.business_description,
        services_and_prices=business.services_and_prices,
        owner_name=business.owner_name,
        lead_handling_preference=business.lead_handling_preference,
        custom_greeting=business.custom_greeting,
        system_prompt=business.system_prompt,
    )


@router.get("/{business_id}/personality", response_model=PersonalityOut)
async def get_personality(
    business_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve agent personality configuration."""
    # Verify user owns this business
    if current_user.business_id != business_id:
        raise HTTPException(status_code=404, detail="Business not found")
    
    result = await db.execute(select(Business).where(Business.id == business_id))
    business = result.scalar_one_or_none()
    
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
    
    return PersonalityOut(
        business_description=business.business_description,
        services_and_prices=business.services_and_prices,
        owner_name=business.owner_name,
        lead_handling_preference=business.lead_handling_preference,
        custom_greeting=business.custom_greeting,
        system_prompt=business.system_prompt,
    )


# Call settings endpoints (Issue #62)
@router.put("/{business_id}/call-settings", response_model=CallSettingsOut)
async def save_call_settings(
    business_id: UUID,
    settings: CallSettingsConfig,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Configure call forwarding settings (ring timeout and owner phone)."""
    # Verify user owns this business
    if current_user.business_id != business_id:
        raise HTTPException(status_code=404, detail="Business not found")
    
    result = await db.execute(select(Business).where(Business.id == business_id))
    business = result.scalar_one_or_none()
    
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
    
    # Update call settings
    business.ring_timeout_seconds = str(settings.ring_timeout_seconds)
    business.owner_phone = settings.owner_phone
    
    await db.commit()
    await db.refresh(business)
    
    return CallSettingsOut(
        ring_timeout_seconds=int(business.ring_timeout_seconds) if business.ring_timeout_seconds else None,
        owner_phone=business.owner_phone,
    )


@router.get("/{business_id}/call-settings", response_model=CallSettingsOut)
async def get_call_settings(
    business_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve call forwarding settings."""
    # Verify user owns this business
    if current_user.business_id != business_id:
        raise HTTPException(status_code=404, detail="Business not found")
    
    result = await db.execute(select(Business).where(Business.id == business_id))
    business = result.scalar_one_or_none()
    
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
    
    return CallSettingsOut(
        ring_timeout_seconds=int(business.ring_timeout_seconds) if business.ring_timeout_seconds else None,
        owner_phone=business.owner_phone,
    )


@router.get("/{business_id}/extracted-metadata")
async def get_extracted_metadata(
    business_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_optional),
):
    """Get extracted business metadata from website/PDF ingestion.
    
    Returns the extracted data plus helpful placeholders for the personality form.
    This allows auto-filling the personality form with scraped data.
    """
    # Verify user owns this business
    if current_user and current_user.business_id != business_id:
        raise HTTPException(status_code=404, detail="Business not found")
    
    result = await db.execute(select(Business).where(Business.id == business_id))
    business = result.scalar_one_or_none()
    
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
    
    # Get extracted metadata (empty dict if none)
    extracted_data = business.extracted_metadata or {}
    
    # Generate helpful placeholders based on extracted data
    placeholders = generate_placeholder_text(extracted_data)
    
    return {
        "extracted_data": extracted_data,
        "placeholders": placeholders,
        "extraction_source": business.extraction_source_url,
        "extracted_at": business.extracted_at,
        "has_extraction": bool(business.extracted_metadata),
    }
