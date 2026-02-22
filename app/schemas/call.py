"""Pydantic schemas for Call API responses and Retell webhook payloads."""

from datetime import datetime
from uuid import UUID
from pydantic import BaseModel


class CallOut(BaseModel):
    """Response schema for call endpoints."""
    id: UUID
    call_id: str
    caller_phone: str | None = None
    business_id: str | None = None
    status: str | None = None
    outcome: str | None = None
    approval_status: str | None = None
    transcript: str | None = None
    summary: str | None = None
    lead_name: str | None = None
    lead_address: str | None = None
    service_type: str | None = None
    urgency: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    class Config:
        from_attributes = True


class RetellCallEndedData(BaseModel):
    """Relevant fields from Retell call_ended payload."""
    call_id: str
    from_number: str | None = None
    to_number: str | None = None
    transcript: str | None = None
    call_analysis: dict | None = None
