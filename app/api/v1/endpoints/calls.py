"""Call log endpoints for the dashboard."""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from app.core.database import get_db
from app.core.deps import get_current_user_optional
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
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    """List recent calls.
    
    If authenticated, returns calls for the user's business only.
    If unauthenticated (legacy mode), returns all calls.
    """
    if current_user:
        # Authenticated: scope to user's business
        result = await db.execute(
            select(Business).where(Business.id == current_user.business_id)
        )
        business = result.scalar_one_or_none()
        
        if not business or not business.retell_agent_id:
            return []
        
        result = await db.execute(
            select(Call)
            .where(Call.business_id == business.retell_agent_id)
            .order_by(Call.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
    else:
        # Unauthenticated: return all calls (backward compatibility)
        result = await db.execute(
            select(Call)
            .order_by(Call.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
    
    return result.scalars().all()


@router.get("/{call_id}", response_model=CallOut)
async def get_call(
    call_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    """Get a single call by Retell call_id.
    
    If authenticated, scopes to user's business.
    If unauthenticated (legacy mode), allows any call.
    """
    if current_user:
        # Authenticated: scope to user's business
        result = await db.execute(
            select(Business).where(Business.id == current_user.business_id)
        )
        business = result.scalar_one_or_none()
        
        if not business or not business.retell_agent_id:
            raise HTTPException(status_code=404, detail="Call not found")
        
        result = await db.execute(
            select(Call).where(
                and_(
                    Call.call_id == call_id,
                    Call.business_id == business.retell_agent_id
                )
            )
        )
    else:
        # Unauthenticated: allow any call (backward compatibility)
        result = await db.execute(
            select(Call).where(Call.call_id == call_id)
        )
    
    call = result.scalar_one_or_none()
    if not call:
        raise HTTPException(status_code=404, detail="Call not found")
    return call


@router.get("/{call_id}/recording")
async def get_call_recording(
    call_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    """Get the call recording URL for playback (Issue #63).
    
    Returns the Azure Blob URL if a recording exists.
    If authenticated, scopes to user's business.
    """
    if current_user:
        # Authenticated: scope to user's business
        result = await db.execute(
            select(Business).where(Business.id == current_user.business_id)
        )
        business = result.scalar_one_or_none()
        
        if not business or not business.retell_agent_id:
            raise HTTPException(status_code=404, detail="Call not found")
        
        result = await db.execute(
            select(Call).where(
                and_(
                    Call.call_id == call_id,
                    Call.business_id == business.retell_agent_id
                )
            )
        )
    else:
        # Unauthenticated: allow any call (backward compatibility)
        result = await db.execute(
            select(Call).where(Call.call_id == call_id)
        )
    
    call = result.scalar_one_or_none()
    if not call:
        raise HTTPException(status_code=404, detail="Call not found")
    
    if not call.recording_url:
        raise HTTPException(status_code=404, detail="No recording available for this call")
    
    return {"recording_url": call.recording_url}
