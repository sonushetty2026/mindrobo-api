"""Business CRUD endpoints — onboard and manage businesses."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.models.business import Business
from app.schemas.business import BusinessCreate, BusinessOut

router = APIRouter()


@router.post("/", response_model=BusinessOut, status_code=201)
async def create_business(biz: BusinessCreate, db: AsyncSession = Depends(get_db)):
    """Onboard a new business."""
    business = Business(**biz.model_dump())
    db.add(business)
    await db.commit()
    await db.refresh(business)
    return business


@router.get("/", response_model=list[BusinessOut])
async def list_businesses(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Business).where(Business.is_active == True).order_by(Business.created_at.desc()))
    return result.scalars().all()


@router.get("/{business_id}", response_model=BusinessOut)
async def get_business(business_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Business).where(Business.id == business_id))
    biz = result.scalar_one_or_none()
    if not biz:
        raise HTTPException(status_code=404, detail="Business not found")
    return biz
