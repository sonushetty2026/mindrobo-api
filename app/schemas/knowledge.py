"""Pydantic schemas for knowledge base."""

from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, HttpUrl


class KnowledgeIngest(BaseModel):
    """Request to ingest a website URL into a business's knowledge base."""
    business_id: UUID
    url: str


class KnowledgeEntryOut(BaseModel):
    id: UUID
    business_id: UUID
    source_url: str
    title: str | None = None
    content: str
    content_type: str
    is_active: bool
    created_at: datetime | None = None
    updated_at: datetime | None = None

    class Config:
        from_attributes = True
