"""Knowledge base endpoints.

- POST /api/v1/knowledge/ingest → scrape a URL and store content
- GET /api/v1/knowledge/{business_id} → list knowledge entries for a business
- DELETE /api/v1/knowledge/{entry_id} → remove a knowledge entry
"""

import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.models.knowledge import KnowledgeEntry
from app.models.business import Business
from app.schemas.knowledge import KnowledgeIngest, KnowledgeEntryOut
from app.services.scraper import scrape_url

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/ingest", response_model=KnowledgeEntryOut, status_code=201)
async def ingest_url(
    data: KnowledgeIngest,
    db: AsyncSession = Depends(get_db),
):
    """Scrape a website URL and store its content as knowledge for a business."""
    # Verify business exists
    result = await db.execute(
        select(Business).where(Business.id == data.business_id)
    )
    business = result.scalar_one_or_none()
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")

    # Check for duplicate URL
    existing = await db.execute(
        select(KnowledgeEntry).where(
            KnowledgeEntry.business_id == data.business_id,
            KnowledgeEntry.source_url == data.url,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=409,
            detail=f"URL {data.url} already ingested for this business"
        )

    # Scrape
    try:
        scraped = await scrape_url(data.url)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    # Determine content type from URL/title
    content_type = _guess_content_type(data.url, scraped.get("title", ""))

    entry = KnowledgeEntry(
        business_id=data.business_id,
        source_url=data.url,
        title=scraped.get("title"),
        content=scraped["content"],
        content_type=content_type,
    )
    db.add(entry)
    await db.commit()
    await db.refresh(entry)
    logger.info(
        "Knowledge ingested: %s → %s (%d chars)",
        data.url, business.name, len(entry.content),
    )
    return entry


@router.get("/{business_id}", response_model=list[KnowledgeEntryOut])
async def list_knowledge(
    business_id: str,
    db: AsyncSession = Depends(get_db),
):
    """List all knowledge entries for a business."""
    result = await db.execute(
        select(KnowledgeEntry)
        .where(
            KnowledgeEntry.business_id == business_id,
            KnowledgeEntry.is_active == True,
        )
        .order_by(KnowledgeEntry.created_at.desc())
    )
    return result.scalars().all()


@router.delete("/{entry_id}", status_code=204)
async def delete_knowledge(
    entry_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Soft-delete a knowledge entry."""
    result = await db.execute(
        select(KnowledgeEntry).where(KnowledgeEntry.id == entry_id)
    )
    entry = result.scalar_one_or_none()
    if not entry:
        raise HTTPException(status_code=404, detail="Knowledge entry not found")

    entry.is_active = False
    await db.commit()
    logger.info("Knowledge entry deactivated: %s", entry_id)


def _guess_content_type(url: str, title: str) -> str:
    """Best-effort guess of content type from URL and title."""
    url_lower = url.lower()
    title_lower = title.lower() if title else ""
    combined = url_lower + " " + title_lower

    if any(w in combined for w in ["faq", "frequently asked", "questions"]):
        return "faq"
    if any(w in combined for w in ["service", "what-we-do", "offerings"]):
        return "services"
    if any(w in combined for w in ["about", "who-we-are", "our-story", "team"]):
        return "about"
    if any(w in combined for w in ["contact", "location", "hours"]):
        return "contact"
    return "webpage"
