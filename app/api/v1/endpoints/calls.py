from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.models.call import Call

router = APIRouter()

@router.get("/")
async def list_calls(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Call).order_by(Call.created_at.desc()).limit(50))
    return result.scalars().all()

@router.get("/{call_id}")
async def get_call(call_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Call).where(Call.call_id == call_id))
    call = result.scalar_one_or_none()
    if not call:
        raise HTTPException(status_code=404, detail="Call not found")
    return call
