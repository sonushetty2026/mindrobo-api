"""Business CRUD endpoints — onboard and manage businesses."""

from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.core.deps import get_current_user, get_current_user_optional
from app.models.business import Business
from app.models.user import User
from app.schemas.business import BusinessCreate, BusinessOut, BusinessUpdate

router = APIRouter()


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
