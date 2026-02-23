"""Pydantic schemas for Business config."""

from datetime import datetime
from uuid import UUID
from pydantic import BaseModel
from app.models.business import LeadHandlingPreference, PhoneSetupType


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


class PersonalityConfig(BaseModel):
    """Agent personality configuration (Issue #59)."""
    business_description: str
    services_and_prices: str
    owner_name: str | None = None
    lead_handling_preference: LeadHandlingPreference


class PersonalityOut(BaseModel):
    """Response schema for personality config."""
    business_description: str | None = None
    services_and_prices: str | None = None
    owner_name: str | None = None
    lead_handling_preference: LeadHandlingPreference | None = None
    custom_greeting: str | None = None
    system_prompt: str | None = None

    class Config:
        from_attributes = True


class PhoneNumberInfo(BaseModel):
    """Available phone number from Twilio."""
    phone_number: str
    friendly_name: str
    locality: str | None = None
    region: str | None = None


class PhonePurchaseRequest(BaseModel):
    """Request to purchase a phone number (Issue #61)."""
    phone_number: str


class PhoneForwardRequest(BaseModel):
    """Request to configure an existing number for forwarding (Issue #61)."""
    phone_number: str


class BusinessOut(BaseModel):
    id: UUID
    name: str
    owner_name: str | None = None
    owner_phone: str
    owner_email: str | None = None
    retell_agent_id: str | None = None
    twilio_phone_number: str | None = None
    stripe_customer_id: str | None = None
    subscription_status: str | None = None
    is_active: bool
    created_at: datetime | None = None
    updated_at: datetime | None = None
    
    # Personality fields
    business_description: str | None = None
    services_and_prices: str | None = None
    lead_handling_preference: LeadHandlingPreference | None = None
    custom_greeting: str | None = None
    system_prompt: str | None = None
    phone_setup_type: PhoneSetupType | None = None

    class Config:
        from_attributes = True
