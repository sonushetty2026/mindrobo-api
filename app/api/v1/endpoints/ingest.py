"""Ingest endpoint for URL/PDF → chunk → review → publish flow.

This replaces the old wizard-style onboarding with a 3-step process:
1. POST /ingest/preview → extract chunks for review
2. (Frontend displays chunks for approval)
3. POST /ingest/publish → save approved chunks to DB
"""

import logging
import re
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.models.knowledge import KnowledgeEntry
from app.models.business import Business
from app.services.scraper import scrape_url
from app.services.pdf_extractor import extract_pdf_text
from app.services.business_extractor import extract_business_metadata
from datetime import datetime
from pydantic import BaseModel

router = APIRouter()
logger = logging.getLogger(__name__)


# ===== Schemas =====

class ChunkOut(BaseModel):
    """A single chunk of extracted content for review."""
    temp_id: str  # Temporary ID for frontend tracking (e.g. "chunk_0")
    content: str
    title: Optional[str] = None
    source_url: str
    content_type: str = "webpage"


class PreviewResponse(BaseModel):
    """Response from /ingest/preview - chunks ready for review."""
    chunks: List[ChunkOut]
    source_url: str
    title: Optional[str] = None
    extracted_metadata: dict = {}  # Business metadata extracted from content


class ChunkToPublish(BaseModel):
    """A chunk approved by the user, ready to save."""
    content: str
    source_url: str
    title: Optional[str] = None
    content_type: str = "webpage"


class PublishRequest(BaseModel):
    """Request to publish approved chunks."""
    business_id: UUID
    chunks: List[ChunkToPublish]


class PublishResponse(BaseModel):
    """Response from /ingest/publish."""
    saved_count: int
    business_id: UUID


# ===== Chunking Logic =====

def _chunk_text(text: str, max_chunk_size: int = 800, overlap: int = 100) -> List[str]:
    """Split text into overlapping chunks for better context preservation.
    
    Strategy:
    - Split by double newlines (paragraphs) first
    - If a paragraph is too long, split by sentences
    - Target ~800 chars per chunk with 100 char overlap
    """
    # Split into paragraphs
    paragraphs = re.split(r'\n\s*\n', text.strip())
    
    chunks = []
    current_chunk = ""
    
    for para in paragraphs:
        para = para.strip()
        if not para:
            continue
        
        # If adding this paragraph doesn't exceed limit, add it
        if len(current_chunk) + len(para) + 2 <= max_chunk_size:
            current_chunk += ("\n\n" if current_chunk else "") + para
        else:
            # Save current chunk if it has content
            if current_chunk:
                chunks.append(current_chunk)
                # Start new chunk with overlap from previous
                overlap_text = current_chunk[-overlap:] if len(current_chunk) > overlap else current_chunk
                current_chunk = overlap_text + "\n\n" + para
            else:
                # Single paragraph is too long - split by sentences
                sentences = re.split(r'(?<=[.!?])\s+', para)
                for sent in sentences:
                    if len(current_chunk) + len(sent) + 1 <= max_chunk_size:
                        current_chunk += (" " if current_chunk else "") + sent
                    else:
                        if current_chunk:
                            chunks.append(current_chunk)
                            overlap_text = current_chunk[-overlap:] if len(current_chunk) > overlap else current_chunk
                            current_chunk = overlap_text + " " + sent
                        else:
                            # Even a single sentence is too long - just truncate
                            chunks.append(sent[:max_chunk_size])
                            current_chunk = ""
    
    # Don't forget the last chunk
    if current_chunk:
        chunks.append(current_chunk)
    
    # Filter out chunks that are too short (likely just overlap fragments)
    chunks = [c.strip() for c in chunks if len(c.strip()) > 50]
    
    return chunks


# ===== Endpoints =====

@router.post("/preview", response_model=PreviewResponse, status_code=200)
async def preview_ingest(
    business_id: UUID = Form(...),
    url: Optional[str] = Form(None),
    pdf_file: Optional[UploadFile] = File(None),
    db: AsyncSession = Depends(get_db),
):
    """Extract chunks from a URL or PDF for review.
    
    Does NOT save to the database yet. Returns chunks for frontend review.
    """
    # Verify business exists
    result = await db.execute(
        select(Business).where(Business.id == business_id)
    )
    business = result.scalar_one_or_none()
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
    
    # Extract content based on source type
    if url:
        try:
            scraped = await scrape_url(url)
            source_url = url
            title = scraped.get("title")
            content = scraped["content"]
            content_type = _guess_content_type(url, title or "")
        except ValueError as e:
            raise HTTPException(status_code=422, detail=str(e))
    
    elif pdf_file:
        # PDF ingestion
        try:
            # Read file content
            file_content = await pdf_file.read()
            filename = pdf_file.filename or "document.pdf"
            
            # Extract text from PDF
            extracted = await extract_pdf_text(file_content, filename)
            
            source_url = f"pdf://{filename}"  # Pseudo-URL for tracking
            title = extracted.get("title") or filename
            content = extracted["content"]
            content_type = _guess_content_type(filename, title)
            
            logger.info(
                "PDF extracted: %s (%d pages, %d chars)",
                filename, extracted.get("page_count", 0), len(content)
            )
        except ValueError as e:
            raise HTTPException(status_code=422, detail=str(e))
        except ImportError as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    else:
        raise HTTPException(
            status_code=400,
            detail="Either 'url' or 'pdf_file' must be provided"
        )
    
    # Extract business metadata from content
    extracted_metadata = extract_business_metadata(content, title or "")
    
    # Store extracted metadata in business record for later use
    business.extracted_metadata = extracted_metadata
    business.extraction_source_url = source_url
    business.extracted_at = datetime.utcnow()
    await db.commit()
    await db.refresh(business)
    
    logger.info("Extracted business metadata: %s", extracted_metadata)
    
    # Chunk the content
    chunks_text = _chunk_text(content)
    
    # Build response with temporary IDs for frontend tracking
    chunks_out = [
        ChunkOut(
            temp_id=f"chunk_{idx}",
            content=chunk,
            title=title,
            source_url=source_url,
            content_type=content_type,
        )
        for idx, chunk in enumerate(chunks_text)
    ]
    
    logger.info(
        "Preview generated: %d chunks from %s for business %s",
        len(chunks_out), source_url, business.name
    )
    
    return PreviewResponse(
        chunks=chunks_out,
        source_url=source_url,
        title=title,
        extracted_metadata=extracted_metadata,
    )


@router.post("/publish", response_model=PublishResponse, status_code=201)
async def publish_chunks(
    data: PublishRequest,
    db: AsyncSession = Depends(get_db),
):
    """Save approved chunks to the knowledge base.
    
    Takes chunks that the user has reviewed/approved and saves them as KnowledgeEntry records.
    """
    # Verify business exists
    result = await db.execute(
        select(Business).where(Business.id == data.business_id)
    )
    business = result.scalar_one_or_none()
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
    
    if not data.chunks:
        raise HTTPException(status_code=400, detail="No chunks provided to publish")
    
    # Save each chunk as a separate KnowledgeEntry
    saved_count = 0
    for chunk in data.chunks:
        entry = KnowledgeEntry(
            business_id=data.business_id,
            source_url=chunk.source_url,
            title=chunk.title,
            content=chunk.content,
            content_type=chunk.content_type,
            is_active=True,
        )
        db.add(entry)
        saved_count += 1
    
    await db.commit()
    
    logger.info(
        "Published %d chunks to knowledge base for business %s (%s)",
        saved_count, business.name, data.business_id
    )
    
    return PublishResponse(
        saved_count=saved_count,
        business_id=data.business_id,
    )


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
