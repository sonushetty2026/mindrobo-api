"""Pydantic schemas for Business config."""

from datetime import datetime
from uuid import UUID
from pydantic import BaseModel


class BusinessCreate(BaseModel):
    name: str
    owner_name: str | None = None
    owner_phone: str
    owner_email: str | None = None
    retell_agent_id: str | None = None
    twilio_phone_number: str | None = None


class BusinessUpdate(BaseModel):
    """Schema for updating business settings."""
    name: str | None = None
    owner_name: str | None = None
    owner_phone: str | None = None
    owner_email: str | None = None
    retell_agent_id: str | None = None
    twilio_phone_number: str | None = None


class BusinessOut(BaseModel):
    id: UUID
    name: str
    owner_name: str | None = None
    owner_phone: str
    owner_email: str | None = None
    retell_agent_id: str | None = None
    twilio_phone_number: str | None = None
    is_active: bool
    created_at: datetime | None = None
    updated_at: datetime | None = None

    class Config:
        from_attributes = True
