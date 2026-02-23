"""Admin-only endpoints for MindRobo API.

All routes require superadmin role.
"""

import logging
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import require_superadmin
from app.models.user import User

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/dashboard")
async def admin_dashboard(
    current_user: User = Depends(require_superadmin),
    db: AsyncSession = Depends(get_db)
):
    """Admin dashboard - placeholder endpoint.
    
    Returns basic admin info. Requires superadmin role.
    """
    return {
        "message": "Admin dashboard",
        "user": current_user.email,
        "role": current_user.role,
        "business_id": str(current_user.business_id)
    }
