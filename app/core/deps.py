"""FastAPI dependencies for authentication and authorization."""

from typing import Optional
from uuid import UUID
from datetime import datetime, timedelta
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.user import User
from app.services.auth import decode_access_token

security = HTTPBearer()
optional_security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Extract and validate the current user from JWT token.
    
    This dependency should be used on all protected endpoints.
    Raises 401 if no token or invalid token.
    """
    token = credentials.credentials
    payload = decode_access_token(token)
    
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user_id: Optional[str] = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )
    
    # Fetch user from database
    result = await db.execute(select(User).where(User.id == UUID(user_id)))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled",
        )
    
    return user


async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(optional_security),
    db: AsyncSession = Depends(get_db),
) -> Optional[User]:
    """Extract and validate the current user from JWT token (optional).
    
    Returns None if no token is provided or token is invalid.
    Use this for endpoints that work with or without authentication.
    """
    if not credentials:
        return None
    
    token = credentials.credentials
    payload = decode_access_token(token)
    
    if not payload:
        return None
    
    user_id: Optional[str] = payload.get("sub")
    if not user_id:
        return None
    
    try:
        result = await db.execute(select(User).where(User.id == UUID(user_id)))
        user = result.scalar_one_or_none()
        
        if user and user.is_active:
            return user
    except Exception:
        pass
    
    return None


async def check_trial_status(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Check if user's trial has expired and account should be paused.
    
    If trial has expired and user hasn't upgraded (no plan_id), set is_paused=True.
    Returns 403 if account is paused.
    
    Grace period: 3 days after trial_ends_at before full pause.
    """
    if not current_user.is_trial:
        # User is not on trial (has paid plan), allow access
        return current_user
    
    if not current_user.trial_ends_at:
        # No trial end date set, allow access (shouldn't happen, but be safe)
        return current_user
    
    now = datetime.utcnow()
    grace_period_end = current_user.trial_ends_at + timedelta(days=3)
    
    # Check if grace period has passed
    if now > grace_period_end:
        # Trial + grace period expired, pause account if not paid
        if not current_user.plan_id:
            if not current_user.is_paused:
                current_user.is_paused = True
                current_user.paused_at = now
                await db.commit()
            
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Trial expired. Please upgrade to a paid plan to continue using MindRobo."
            )
    
    return current_user
