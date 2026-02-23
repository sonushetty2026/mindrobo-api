"""Leads endpoints for lead capture and management.

- GET /api/v1/leads/ → Lead list page (HTML)
- GET /api/v1/leads/ → List leads (JSON with query params)
- GET /api/v1/leads/stats → Lead stats for dashboard widget
- POST /api/v1/leads/ → Create new lead
- PUT /api/v1/leads/{id}/status → Update lead status
"""

import logging
from pathlib import Path
from typing import List, Optional
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Query, HTTPException
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from pydantic import BaseModel

from app.core.database import get_db

router = APIRouter()
logger = logging.getLogger(__name__)

# Load leads template
TEMPLATES_DIR = Path(__file__).parent.parent.parent.parent / "app" / "templates"
LEADS_TEMPLATE_PATH = TEMPLATES_DIR / "leads.html"


def _load_leads_template() -> str:
    """Load the leads HTML template from file."""
    if not LEADS_TEMPLATE_PATH.exists():
        logger.error("Leads template not found at %s", LEADS_TEMPLATE_PATH)
        return "<html><body><h1>Leads template not found</h1></body></html>"
    return LEADS_TEMPLATE_PATH.read_text()


# Pydantic schemas
class LeadCreate(BaseModel):
    business_id: str
    caller_name: Optional[str] = None
    caller_phone: str
    service_needed: Optional[str] = None
    notes: Optional[str] = None
    source: str = "call"  # call or web
    status: str = "new"  # new, contacted, converted, lost


class LeadStatusUpdate(BaseModel):
    status: str  # new, contacted, converted, lost


class LeadResponse(BaseModel):
    id: int
    business_id: str
    caller_name: Optional[str]
    caller_phone: str
    service_needed: Optional[str]
    notes: Optional[str]
    source: str
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


class LeadStats(BaseModel):
    total_leads: int
    new_leads_today: int
    new_leads_this_week: int
    conversion_rate: float


@router.get("/", response_class=HTMLResponse)
async def leads_page():
    """Serve the leads HTML page."""
    return _load_leads_template()


@router.get("/", response_model=List[LeadResponse])
async def list_leads(
    business_id: str = Query(..., description="Business ID to filter leads"),
    status: Optional[str] = Query(None, description="Filter by status"),
    source: Optional[str] = Query(None, description="Filter by source"),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db)
):
    """List leads for a business with optional filters."""
    from app.models.call import Lead  # Import here to avoid circular dependency
    
    query = select(Lead).where(Lead.business_id == business_id)
    
    if status:
        query = query.where(Lead.status == status)
    
    if source:
        query = query.where(Lead.source == source)
    
    query = query.order_by(Lead.created_at.desc()).limit(limit)
    
    result = await db.execute(query)
    leads = result.scalars().all()
    
    return leads


@router.get("/stats", response_model=LeadStats)
async def lead_stats(
    business_id: str = Query(..., description="Business ID"),
    db: AsyncSession = Depends(get_db)
):
    """Get lead statistics for dashboard widget."""
    from app.models.call import Lead
    
    # Total leads
    total_query = select(func.count(Lead.id)).where(Lead.business_id == business_id)
    total_result = await db.execute(total_query)
    total_leads = total_result.scalar() or 0
    
    # New leads today
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    today_query = select(func.count(Lead.id)).where(
        Lead.business_id == business_id,
        Lead.created_at >= today_start,
        Lead.status == "new"
    )
    today_result = await db.execute(today_query)
    new_today = today_result.scalar() or 0
    
    # New leads this week
    week_start = today_start - timedelta(days=today_start.weekday())
    week_query = select(func.count(Lead.id)).where(
        Lead.business_id == business_id,
        Lead.created_at >= week_start,
        Lead.status == "new"
    )
    week_result = await db.execute(week_query)
    new_week = week_result.scalar() or 0
    
    # Conversion rate
    converted_query = select(func.count(Lead.id)).where(
        Lead.business_id == business_id,
        Lead.status == "converted"
    )
    converted_result = await db.execute(converted_query)
    converted = converted_result.scalar() or 0
    
    conversion_rate = (converted / total_leads * 100) if total_leads > 0 else 0.0
    
    return LeadStats(
        total_leads=total_leads,
        new_leads_today=new_today,
        new_leads_this_week=new_week,
        conversion_rate=round(conversion_rate, 1)
    )


@router.post("/", response_model=LeadResponse)
async def create_lead(
    lead: LeadCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create a new lead."""
    from app.models.call import Lead
    
    db_lead = Lead(
        business_id=lead.business_id,
        caller_name=lead.caller_name,
        caller_phone=lead.caller_phone,
        service_needed=lead.service_needed,
        notes=lead.notes,
        source=lead.source,
        status=lead.status
    )
    
    db.add(db_lead)
    await db.commit()
    await db.refresh(db_lead)
    
    logger.info(
        "Created lead %d for business %s: %s (%s)",
        db_lead.id,
        lead.business_id,
        lead.caller_name or "Unknown",
        lead.caller_phone
    )
    
    return db_lead


@router.put("/{lead_id}/status", response_model=LeadResponse)
async def update_lead_status(
    lead_id: int,
    status_update: LeadStatusUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Update lead status."""
    from app.models.call import Lead
    
    # Fetch lead
    result = await db.execute(select(Lead).where(Lead.id == lead_id))
    lead = result.scalar_one_or_none()
    
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    # Validate status
    valid_statuses = ["new", "contacted", "converted", "lost"]
    if status_update.status not in valid_statuses:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status. Must be one of: {', '.join(valid_statuses)}"
        )
    
    # Update status
    lead.status = status_update.status
    await db.commit()
    await db.refresh(lead)
    
    logger.info("Updated lead %d status to %s", lead_id, status_update.status)
    
    return lead
