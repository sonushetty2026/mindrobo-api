"""Pydantic schemas for Leads."""

from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, EmailStr
from typing import Optional
from app.models.lead import LeadSource, LeadStatus


class LeadCreate(BaseModel):
    """Schema for creating a lead."""
    business_id: UUID
    caller_name: str
    caller_phone: str
    caller_email: Optional[EmailStr] = None
    service_needed: Optional[str] = None
    notes: Optional[str] = None
    source: LeadSource = LeadSource.MANUAL


class LeadOut(BaseModel):
    """Schema for returning lead details."""
    id: UUID
    business_id: UUID
    caller_name: str
    caller_phone: str
    caller_email: Optional[str] = None
    service_needed: Optional[str] = None
    notes: Optional[str] = None
    source: LeadSource
    status: LeadStatus
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class LeadStatusUpdate(BaseModel):
    """Schema for updating lead status."""
    status: LeadStatus


class LeadStatsOut(BaseModel):
    """Schema for lead statistics."""
    new: int
    contacted: int
    converted: int
    lost: int
    total: int
