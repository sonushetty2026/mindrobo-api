"""Admin audit log service."""

import logging
from datetime import datetime
from typing import Optional, Dict, Any
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.admin_audit_log import AdminAuditLog

logger = logging.getLogger(__name__)


async def log_admin_action(
    db: AsyncSession,
    admin_id: UUID,
    action: str,
    target_user_id: Optional[UUID] = None,
    details: Optional[Dict[str, Any]] = None
) -> AdminAuditLog:
    """Log an admin action to the audit trail.
    
    Args:
        db: Database session
        admin_id: UUID of the admin performing the action
        action: Action type (e.g., "user_pause", "trial_extend", "broadcast")
        target_user_id: UUID of the target user (if applicable)
        details: Additional JSON details about the action
    
    Returns:
        The created audit log entry
    """
    audit_entry = AdminAuditLog(
        admin_id=admin_id,
        action=action,
        target_user_id=target_user_id,
        details=details or {}
    )
    
    db.add(audit_entry)
    await db.commit()
    await db.refresh(audit_entry)
    
    logger.info(
        f"Audit log created: admin={admin_id} action={action} target={target_user_id}"
    )
    
    return audit_entry
