"""FastAPI dependencies for authentication."""

from typing import List
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID

from app.core.database import get_db
from app.core.auth import decode_token
from app.models.user import User

security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> User:
    """Extract and validate JWT token, return current user."""
    
    token = credentials.credentials
    payload = decode_token(token)
    
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user_id_str: str | None = payload.get("sub")
    if user_id_str is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload"
        )
    
    try:
        user_id = UUID(user_id_str)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user ID in token"
        )
    
    # Fetch user from database
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    
    return user


def require_role(*roles: str):
    """Dependency factory that checks if user has one of the required roles.
    
    Usage:
        require_admin = require_role("admin", "superadmin")
        
        @router.get("/admin-only")
        async def admin_route(user: User = Depends(require_admin)):
            ...
    """
    async def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required role: {', '.join(roles)}"
            )
        return current_user
    
    return role_checker


# Pre-configured role dependencies
require_admin = require_role("admin", "superadmin")
require_superadmin = require_role("superadmin")
require_support = require_role("support", "admin", "superadmin")  # Support has read access


async def check_rate_limit_dependency(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> User:
    """Dependency that checks API rate limits for the current user.
    
    Issue #100: Trial users limited to 50 API calls/day, paid users to 1000/day.
    
    Raises HTTPException 429 if rate limit exceeded.
    Returns the user if within limits.
    
    Usage:
        @router.get("/rate-limited-endpoint")
        async def my_endpoint(user: User = Depends(check_rate_limit_dependency)):
            ...
    """
    from app.services.rate_limit_service import check_api_rate_limit
    
    await check_api_rate_limit(db, current_user)
    return current_user
