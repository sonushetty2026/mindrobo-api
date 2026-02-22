"""Analytics endpoints for business insights."""

import logging
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, and_
from app.core.database import get_db
from app.models.call import Call

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/calls-per-day")
async def calls_per_day(
    business_id: str,
    days: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db)
):
    """Get calls per day for the last N days."""
    
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    
    # Group by date (cast timestamp to date)
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
    
    result = await db.execute(stmt)
    rows = result.all()
    
    return {
        "period_days": days,
        "data": [{"date": str(row.date), "calls": row.count} for row in rows]
    }


@router.get("/topics")
async def top_topics(
    business_id: str,
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db)
):
    """Get top service types (topics) from calls."""
    
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
    
    result = await db.execute(stmt)
    rows = result.all()
    
    return {
        "topics": [
            {"service_type": row.service_type, "call_count": row.count}
            for row in rows
        ]
    }


@router.get("/missed")
async def missed_calls(
    business_id: str,
    limit: int = Query(50, ge=1, le=500),
    db: AsyncSession = Depends(get_db)
):
    """Get calls where AI couldn't resolve (no lead captured)."""
    
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
    business_id: str,
    days: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db)
):
    """Get overall analytics summary for business."""
    
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    
    # Total calls
    total_stmt = select(func.count(Call.id)).where(
        and_(
            Call.business_id == business_id,
            Call.created_at >= cutoff_date
        )
    )
    total_result = await db.execute(total_stmt)
    total_calls = total_result.scalar() or 0
    
    # Successful resolutions (lead_captured)
    success_stmt = select(func.count(Call.id)).where(
        and_(
            Call.business_id == business_id,
            Call.created_at >= cutoff_date,
            Call.outcome == 'lead_captured'
        )
    )
    success_result = await db.execute(success_stmt)
    successful_calls = success_result.scalar() or 0
    
    # Resolution rate
    resolution_rate = (successful_calls / total_calls * 100) if total_calls > 0 else 0.0
    
    # Urgency breakdown
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
    urgency_result = await db.execute(urgency_stmt)
    urgency_breakdown = {row.urgency: row.count for row in urgency_result.all()}
    
    return {
        "period_days": days,
        "total_calls": total_calls,
        "successful_calls": successful_calls,
        "missed_calls": total_calls - successful_calls,
        "resolution_rate_percent": round(resolution_rate, 2),
        "urgency_breakdown": urgency_breakdown,
        "avg_calls_per_day": round(total_calls / days, 2) if days > 0 else 0
    }
