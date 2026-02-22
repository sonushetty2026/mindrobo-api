"""Call log endpoints for the dashboard."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.call import Call
from app.models.user import User
from app.models.business import Business
from app.schemas.call import CallOut

router = APIRouter()


@router.get("/", response_model=list[CallOut])
async def list_calls(
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List recent calls for the authenticated user's business, newest first."""
    # Get the user's business to find their retell_agent_id
    result = await db.execute(
        select(Business).where(Business.id == current_user.business_id)
    )
    business = result.scalar_one_or_none()
    
    if not business or not business.retell_agent_id:
        return []
    
    # Query calls scoped to this business
    result = await db.execute(
        select(Call)
        .where(Call.business_id == business.retell_agent_id)
        .order_by(Call.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return result.scalars().all()


@router.get("/{call_id}", response_model=CallOut)
async def get_call(
    call_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a single call by Retell call_id, scoped to the user's business."""
    # Get the user's business
    result = await db.execute(
        select(Business).where(Business.id == current_user.business_id)
    )
    business = result.scalar_one_or_none()
    
    if not business or not business.retell_agent_id:
        raise HTTPException(status_code=404, detail="Call not found")
    
    # Query call scoped to this business
    result = await db.execute(
        select(Call).where(
            and_(
                Call.call_id == call_id,
                Call.business_id == business.retell_agent_id
            )
        )
    )
    call = result.scalar_one_or_none()
    if not call:
        raise HTTPException(status_code=404, detail="Call not found")
    return call
