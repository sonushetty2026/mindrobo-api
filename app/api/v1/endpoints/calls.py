"""Call log endpoints for the dashboard."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.models.call import Call
from app.schemas.call import CallOut

router = APIRouter()


@router.get("/", response_model=list[CallOut])
async def list_calls(
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
):
    """List recent calls, newest first."""
    result = await db.execute(
        select(Call)
        .order_by(Call.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return result.scalars().all()


@router.get("/{call_id}", response_model=CallOut)
async def get_call(call_id: str, db: AsyncSession = Depends(get_db)):
    """Get a single call by Retell call_id."""
    result = await db.execute(select(Call).where(Call.call_id == call_id))
    call = result.scalar_one_or_none()
    if not call:
        raise HTTPException(status_code=404, detail="Call not found")
    return call
