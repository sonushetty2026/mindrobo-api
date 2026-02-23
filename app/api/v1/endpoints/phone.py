"""Phone number management endpoints (Issue #61)."""

import os
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.business import Business, PhoneSetupType
from app.models.user import User
from app.schemas.business import (
    PhoneNumberInfo,
    PhonePurchaseRequest,
    PhoneForwardRequest,
    BusinessOut,
)

router = APIRouter()


def get_twilio_client():
    """Get configured Twilio client or raise 503 if credentials missing."""
    account_sid = os.getenv("TWILIO_ACCOUNT_SID")
    auth_token = os.getenv("TWILIO_AUTH_TOKEN")
    
    if not account_sid or not auth_token:
        raise HTTPException(
            status_code=503,
            detail="Phone service not configured. Please contact support."
        )
    
    try:
        from twilio.rest import Client
        return Client(account_sid, auth_token)
    except ImportError:
        raise HTTPException(
            status_code=503,
            detail="Twilio SDK not installed. Please contact support."
        )


@router.get("/available", response_model=list[PhoneNumberInfo])
async def search_available_numbers(
    area_code: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Search for available local phone numbers via Twilio.
    
    Query params:
    - area_code: Optional 3-digit area code (e.g., "415", "212")
    
    Returns up to 10 available numbers.
    """
    client = get_twilio_client()
    
    try:
        # Search for local numbers in US
        search_params = {
            "country": "US",
            "limit": 10,
        }
        
        if area_code:
            # Validate area code format
            if not area_code.isdigit() or len(area_code) != 3:
                raise HTTPException(
                    status_code=400,
                    detail="Area code must be a 3-digit number"
                )
            search_params["area_code"] = area_code
        
        available = client.available_phone_numbers("US").local.list(**search_params)
        
        if not available:
            raise HTTPException(
                status_code=404,
                detail=f"No available numbers found{f' in area code {area_code}' if area_code else ''}"
            )
        
        return [
            PhoneNumberInfo(
                phone_number=num.phone_number,
                friendly_name=num.friendly_name,
                locality=num.locality,
                region=num.region,
            )
            for num in available
        ]
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error searching phone numbers: {str(e)}"
        )


@router.post("/purchase", response_model=BusinessOut)
async def purchase_phone_number(
    request: PhonePurchaseRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Purchase a phone number from Twilio and assign to the business."""
    client = get_twilio_client()
    
    # Get user's business
    result = await db.execute(
        select(Business).where(Business.id == current_user.business_id)
    )
    business = result.scalar_one_or_none()
    
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
    
    try:
        # Purchase the number
        incoming_number = client.incoming_phone_numbers.create(
            phone_number=request.phone_number,
            friendly_name=f"{business.name} - MindRobo",
        )
        
        # Save to business record
        business.twilio_phone_number = incoming_number.phone_number
        business.phone_setup_type = PhoneSetupType.PURCHASED
        
        await db.commit()
        await db.refresh(business)
        
        return business
    
    except Exception as e:
        # Twilio errors come through here
        error_msg = str(e)
        if "Unable to create record" in error_msg:
            raise HTTPException(
                status_code=400,
                detail=f"Unable to purchase number. It may no longer be available: {error_msg}"
            )
        elif "authenticate" in error_msg.lower():
            raise HTTPException(
                status_code=503,
                detail="Twilio authentication failed. Please contact support."
            )
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Error purchasing phone number: {error_msg}"
            )


@router.post("/forward", response_model=BusinessOut)
async def configure_forwarding(
    request: PhoneForwardRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Configure an existing phone number for call forwarding.
    
    This endpoint just saves the number to the business record.
    Actual forwarding setup is done manually or via Twilio console.
    """
    # Get user's business
    result = await db.execute(
        select(Business).where(Business.id == current_user.business_id)
    )
    business = result.scalar_one_or_none()
    
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
    
    # Validate phone number format (basic E.164 check)
    phone = request.phone_number.strip()
    if not phone.startswith("+") or not phone[1:].replace(" ", "").isdigit():
        raise HTTPException(
            status_code=400,
            detail="Phone number must be in E.164 format (e.g., +14155551234)"
        )
    
    # Save forwarding config
    business.twilio_phone_number = phone
    business.phone_setup_type = PhoneSetupType.FORWARDED
    
    await db.commit()
    await db.refresh(business)
    
    return business
