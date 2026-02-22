"""Pydantic schemas for business onboarding."""

from pydantic import BaseModel, Field, field_validator
from typing import List, Dict, Optional
import re


class FAQ(BaseModel):
    """FAQ question-answer pair."""
    question: str = Field(..., min_length=3, max_length=500)
    answer: str = Field(..., min_length=3, max_length=2000)


class BusinessOnboardingRequest(BaseModel):
    """Request schema for business onboarding."""
    business_name: str = Field(..., min_length=2, max_length=200)
    owner_phone: str = Field(..., pattern=r"^\+?1?\d{10,15}$")
    industry: str = Field(..., min_length=2, max_length=100)
    hours_of_operation: Optional[Dict[str, str]] = None
    greeting_script: Optional[str] = Field(None, max_length=1000)
    faqs: Optional[List[FAQ]] = Field(default_factory=list)
    
    @field_validator("owner_phone")
    @classmethod
    def validate_phone(cls, v):
        # Remove non-digits
        digits = re.sub(r"\D", "", v)
        if len(digits) < 10 or len(digits) > 15:
            raise ValueError("Phone number must be 10-15 digits")
        # Format with +1 prefix if not present
        if not v.startswith("+"):
            v = f"+1{digits[-10:]}"
        return v


class AgentConfigRequest(BaseModel):
    """Request schema for updating agent config."""
    greeting_script: Optional[str] = Field(None, max_length=1000)
    faqs: Optional[List[FAQ]] = None
    hours_of_operation: Optional[Dict[str, str]] = None
    industry: Optional[str] = Field(None, max_length=100)


class AgentConfigResponse(BaseModel):
    """Response schema for agent config."""
    business_id: str
    business_name: str
    industry: Optional[str]
    hours_of_operation: Optional[Dict[str, str]]
    greeting_script: Optional[str]
    faqs: Optional[List[Dict[str, str]]]
    
    class Config:
        from_attributes = True


class TestCallResponse(BaseModel):
    """Response schema for test call simulation."""
    greeting: str
    business_name: str
    hours: Optional[str]
    sample_faqs: Optional[List[str]]
