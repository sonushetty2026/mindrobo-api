"""Lead management endpoints."""

from datetime import datetime
from typing import Optional, List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
from app.core.database import get_db
from app.models.business import Business
from app.models.lead import Lead, LeadStatus
from app.models.user import User
from app.schemas.lead import LeadCreate, LeadOut, LeadStatusUpdate, LeadStatsOut
from app.core.trial_limits import check_trial_limit_leads
import logging

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/", response_model=LeadOut)
async def create_lead(
    lead_data: LeadCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create a new lead (with trial limit check)."""
    # Verify business exists
    result = await db.execute(select(Business).where(Business.id == lead_data.business_id))
    business = result.scalar_one_or_none()
    
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
    
    # Get the business owner (user) to check trial status
    user_result = await db.execute(
        select(User).where(User.business_id == lead_data.business_id)
    )
    user = user_result.scalars().first()
    
    if user:
        # Check trial limits before creating lead
        await check_trial_limit_leads(db, lead_data.business_id, user)
    
    # Create lead
    lead = Lead(
        business_id=lead_data.business_id,
        caller_name=lead_data.caller_name,
        caller_phone=lead_data.caller_phone,
        caller_email=lead_data.caller_email,
        service_needed=lead_data.service_needed,
        notes=lead_data.notes,
        source=lead_data.source,
        status=LeadStatus.NEW,
    )
    
    db.add(lead)
    await db.commit()
    await db.refresh(lead)
    
    logger.info(f"Created lead {lead.id} for business {business.id}")
    
    return lead


@router.get("/", response_model=List[LeadOut])
async def list_leads(
    business_id: Optional[UUID] = Query(None),
    status: Optional[LeadStatus] = Query(None),
    limit: int = Query(100, le=1000),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """List leads with optional filters."""
    query = select(Lead)
    
    filters = []
    if business_id:
        filters.append(Lead.business_id == business_id)
    if status:
        filters.append(Lead.status == status)
    
    if filters:
        query = query.where(and_(*filters))
    
    query = query.order_by(Lead.created_at.desc()).limit(limit).offset(offset)
    
    result = await db.execute(query)
    leads = result.scalars().all()
    
    return leads


@router.put("/{lead_id}/status", response_model=LeadOut)
async def update_lead_status(
    lead_id: UUID,
    status_update: LeadStatusUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update lead status."""
    result = await db.execute(select(Lead).where(Lead.id == lead_id))
    lead = result.scalar_one_or_none()
    
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    lead.status = status_update.status
    lead.updated_at = datetime.utcnow()
    
    await db.commit()
    await db.refresh(lead)
    
    logger.info(f"Updated lead {lead_id} status to {status_update.status}")
    
    return lead


@router.get("/stats", response_model=LeadStatsOut)
async def get_lead_stats(
    business_id: Optional[UUID] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Get lead statistics."""
    from sqlalchemy import case, cast, String
    status_text = cast(Lead.status, String)
    query = select(
        func.count(Lead.id).label("total"),
        func.sum(case((status_text == "new", 1), else_=0)).label("new"),
        func.sum(case((status_text == "contacted", 1), else_=0)).label("contacted"),
        func.sum(case((status_text == "converted", 1), else_=0)).label("converted"),
        func.sum(case((status_text == "lost", 1), else_=0)).label("lost"),
    )
    
    if business_id:
        query = query.where(Lead.business_id == business_id)
    
    result = await db.execute(query)
    row = result.one()
    
    return LeadStatsOut(
        total=row.total or 0,
        new=int(row.new or 0),
        contacted=int(row.contacted or 0),
        converted=int(row.converted or 0),
        lost=int(row.lost or 0),
    )
