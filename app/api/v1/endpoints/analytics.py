"""Analytics endpoints for dashboard charts and stats.

- GET /api/v1/analytics/ → HTML analytics dashboard page
- GET /api/v1/analytics/stats → aggregated call statistics
- GET /api/v1/analytics/calls-per-day → calls grouped by day
- GET /api/v1/analytics/topics → top call topics/services
- GET /api/v1/analytics/missed → missed/unresolved calls
- GET /api/v1/analytics/summary → overall analytics summary
"""

import logging
from datetime import datetime, timedelta
from pathlib import Path

from fastapi import APIRouter, Depends, Query
from fastapi.responses import HTMLResponse
from sqlalchemy import and_, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.call import Call

router = APIRouter()
logger = logging.getLogger(__name__)

# Load analytics template
TEMPLATES_DIR = Path(__file__).resolve().parent.parent.parent.parent / "templates"
ANALYTICS_TEMPLATE_PATH = TEMPLATES_DIR / "analytics.html"


def _load_analytics_template() -> str:
    """Load the analytics HTML template from file."""
    if not ANALYTICS_TEMPLATE_PATH.exists():
        logger.error("Analytics template not found at %s", ANALYTICS_TEMPLATE_PATH)
        return "<html><body><h1>Analytics template not found</h1></body></html>"
    return ANALYTICS_TEMPLATE_PATH.read_text()


@router.get("/", response_class=HTMLResponse)
async def analytics_page():
    """Serve the analytics dashboard HTML."""
    return _load_analytics_template()


@router.get("/stats")
async def get_stats(business_id: str = None, db: AsyncSession = Depends(get_db)):
    """Get aggregated call statistics."""
    # Build base query
    if business_id:
        total_q = select(func.count(Call.id)).where(Call.business_id == business_id)
        leads_q = select(func.count(Call.id)).where(
            and_(Call.business_id == business_id, Call.outcome == "lead_captured")
        )
        callbacks_q = select(func.count(Call.id)).where(
            and_(Call.business_id == business_id, Call.outcome == "callback_scheduled")
        )
        completed_q = select(func.count(Call.id)).where(
            and_(Call.business_id == business_id, Call.status == "completed")
        )
        missed_q = select(func.count(Call.id)).where(
            and_(Call.business_id == business_id, Call.status == "failed")
        )
    else:
        total_q = select(func.count(Call.id))
        leads_q = select(func.count(Call.id)).where(Call.outcome == "lead_captured")
        callbacks_q = select(func.count(Call.id)).where(Call.outcome == "callback_scheduled")
        completed_q = select(func.count(Call.id)).where(Call.status == "completed")
        missed_q = select(func.count(Call.id)).where(Call.status == "failed")
    
    # Execute queries
    total_calls = (await db.execute(total_q)).scalar() or 0
    leads_captured = (await db.execute(leads_q)).scalar() or 0
    callbacks_scheduled = (await db.execute(callbacks_q)).scalar() or 0
    completed_calls = (await db.execute(completed_q)).scalar() or 0
    missed_calls = (await db.execute(missed_q)).scalar() or 0
    
    # Resolution rate
    resolution_rate = (
        round((leads_captured + callbacks_scheduled) / total_calls * 100, 1)
        if total_calls > 0
        else 0
    )
    
    return {
        "total_calls": total_calls,
        "leads_captured": leads_captured,
        "callbacks_scheduled": callbacks_scheduled,
        "completed_calls": completed_calls,
        "missed_calls": missed_calls,
        "resolution_rate": resolution_rate,
        "avg_duration_seconds": 180,  # TODO: Calculate from actual call duration when available
    }


@router.get("/calls-per-day")
async def calls_per_day(
    business_id: str = None,
    days: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db)
):
    """Get calls per day for the last N days."""
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    
    # Build query with optional business filter
    if business_id:
        stmt = (
            select(
                func.date(Call.created_at).label('date'),
                func.count(Call.id).label('count')
            )
            .where(
                and_(
                    Call.business_id == business_id,
                    Call.created_at >= cutoff_date
                )
            )
            .group_by(func.date(Call.created_at))
            .order_by(func.date(Call.created_at))
        )
    else:
        stmt = (
            select(
                func.date(Call.created_at).label('date'),
                func.count(Call.id).label('count')
            )
            .where(Call.created_at >= cutoff_date)
            .group_by(func.date(Call.created_at))
            .order_by(func.date(Call.created_at))
        )
    
    result = await db.execute(stmt)
    rows = result.all()
    
    # Fill in missing days with 0
    date_map = {row.date.isoformat(): row.count for row in rows}
    daily_data = []
    
    start_date = cutoff_date
    for i in range(days):
        day = start_date + timedelta(days=i)
        date_str = day.date().isoformat()
        daily_data.append({
            "date": date_str,
            "count": date_map.get(date_str, 0),
        })
    
    return {"daily_calls": daily_data}


@router.get("/topics")
async def top_topics(
    business_id: str = None,
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db)
):
    """Get top service types (topics) from calls."""
    if business_id:
        stmt = (
            select(
                Call.service_type,
                func.count(Call.id).label('count')
            )
            .where(
                and_(
                    Call.business_id == business_id,
                    Call.service_type.isnot(None)
                )
            )
            .group_by(Call.service_type)
            .order_by(desc('count'))
            .limit(limit)
        )
    else:
        stmt = (
            select(
                Call.service_type,
                func.count(Call.id).label('count')
            )
            .where(Call.service_type.isnot(None))
            .group_by(Call.service_type)
            .order_by(desc('count'))
            .limit(limit)
        )
    
    result = await db.execute(stmt)
    rows = result.all()
    
    return {
        "topics": [
            {"name": row.service_type or "Unknown", "count": row.count}
            for row in rows
        ]
    }


@router.get("/missed")
async def missed_calls(
    business_id: str = None,
    limit: int = Query(50, ge=1, le=500),
    db: AsyncSession = Depends(get_db)
):
    """Get calls where AI couldn't resolve (no lead captured)."""
    if business_id:
        stmt = (
            select(Call)
            .where(
                and_(
                    Call.business_id == business_id,
                    Call.outcome != 'lead_captured'
                )
            )
            .order_by(desc(Call.created_at))
            .limit(limit)
        )
    else:
        stmt = (
            select(Call)
            .where(Call.outcome != 'lead_captured')
            .order_by(desc(Call.created_at))
            .limit(limit)
        )
    
    result = await db.execute(stmt)
    calls = result.scalars().all()
    
    return {
        "missed_count": len(calls),
        "calls": [
            {
                "call_id": c.call_id,
                "caller_phone": c.caller_phone,
                "outcome": c.outcome,
                "summary": c.summary,
                "created_at": c.created_at.isoformat() if c.created_at else None
            }
            for c in calls
        ]
    }


@router.get("/summary")
async def analytics_summary(
    business_id: str = None,
    days: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db)
):
    """Get overall analytics summary."""
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    
    # Build queries with optional business filter
    if business_id:
        total_stmt = select(func.count(Call.id)).where(
            and_(
                Call.business_id == business_id,
                Call.created_at >= cutoff_date
            )
        )
        success_stmt = select(func.count(Call.id)).where(
            and_(
                Call.business_id == business_id,
                Call.created_at >= cutoff_date,
                Call.outcome == 'lead_captured'
            )
        )
        urgency_stmt = (
            select(
                Call.urgency,
                func.count(Call.id).label('count')
            )
            .where(
                and_(
                    Call.business_id == business_id,
                    Call.created_at >= cutoff_date,
                    Call.urgency.isnot(None)
                )
            )
            .group_by(Call.urgency)
        )
    else:
        total_stmt = select(func.count(Call.id)).where(Call.created_at >= cutoff_date)
        success_stmt = select(func.count(Call.id)).where(
            and_(
                Call.created_at >= cutoff_date,
                Call.outcome == 'lead_captured'
            )
        )
        urgency_stmt = (
            select(
                Call.urgency,
                func.count(Call.id).label('count')
            )
            .where(
                and_(
                    Call.created_at >= cutoff_date,
                    Call.urgency.isnot(None)
                )
            )
            .group_by(Call.urgency)
        )
    
    # Execute queries
    total_result = await db.execute(total_stmt)
    total_calls = total_result.scalar() or 0
    
    success_result = await db.execute(success_stmt)
    successful_calls = success_result.scalar() or 0
    
    urgency_result = await db.execute(urgency_stmt)
    urgency_breakdown = {row.urgency: row.count for row in urgency_result.all()}
    
    # Resolution rate
    resolution_rate = (successful_calls / total_calls * 100) if total_calls > 0 else 0.0
    
    return {
        "period_days": days,
        "total_calls": total_calls,
        "successful_calls": successful_calls,
        "missed_calls": total_calls - successful_calls,
        "resolution_rate_percent": round(resolution_rate, 2),
        "urgency_breakdown": urgency_breakdown,
        "avg_calls_per_day": round(total_calls / days, 2) if days > 0 else 0
    }
