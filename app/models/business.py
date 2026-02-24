"""Business configuration model.

Each business (roofing contractor etc.) has config stored here:
owner phone, business name, Retell agent ID mapping, etc.
"""

from sqlalchemy import Column, String, DateTime, Boolean, Text, Integer, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.types import JSON
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime
from enum import Enum
from app.core.database import Base


class LeadHandlingPreference(str, Enum):
    """How the AI should handle customer inquiries."""
    BOOK_APPOINTMENT = "book_appointment"
    SEND_SMS = "send_sms"
    TAKE_MESSAGE = "take_message"


class PhoneSetupType(str, Enum):
    """How the business phone number was configured."""
    PURCHASED = "purchased"
    FORWARDED = "forwarded"


class Business(Base):
    __tablename__ = "businesses"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    owner_name = Column(String, nullable=True)
    owner_phone = Column(String, nullable=False)
    owner_email = Column(String, nullable=True)
    retell_agent_id = Column(String, unique=True, index=True, nullable=True)
    twilio_phone_number = Column(String, nullable=True)  # dedicated inbound number
    stripe_customer_id = Column(String, unique=True, nullable=True)
    subscription_status = Column(String, default="trial")  # trial, active, past_due, canceled
    is_active = Column(Boolean, default=True)
    
    # Onboarding progress tracking
    onboarding_step = Column(Integer, default=0, nullable=False)  # 0=not started, 1=ingested, 2=personality, 3=review, 4=published/complete
    onboarding_completed_at = Column(DateTime, nullable=True)
    
    # Onboarding/config fields (use JSON for SQLite compatibility, will be JSONB in Postgres)
    industry = Column(String, nullable=True)
    hours_of_operation = Column(JSON, nullable=True)  # {"mon": "9-5", "tue": "9-5", ...}
    greeting_script = Column(Text, nullable=True)
    faqs = Column(JSON, nullable=True)  # [{"question": "...", "answer": "..."}, ...]
    
    # Personality builder fields (Issue #59)
    business_description = Column(Text, nullable=True)
    services_and_prices = Column(Text, nullable=True)
    lead_handling_preference = Column(
        SQLEnum(LeadHandlingPreference, name="lead_handling_preference_enum"),
        nullable=True
    )
    custom_greeting = Column(Text, nullable=True)  # auto-generated from personality
    system_prompt = Column(Text, nullable=True)  # auto-generated Retell prompt
    
    # Phone setup tracking (Issue #61)
    phone_setup_type = Column(
        SQLEnum(PhoneSetupType, name="phone_setup_type_enum"),
        nullable=True
    )
    
    # Call forwarding settings (Issue #62)
    ring_timeout_seconds = Column(String, default="20", nullable=True)  # How long to ring before forwarding
    
    # Availability/Scheduling fields
    working_days = Column(JSON, nullable=True)  # ["mon", "tue", "wed", "thu", "fri"]
    working_hours_start = Column(String, nullable=True)  # "08:00"
    working_hours_end = Column(String, nullable=True)  # "18:00"
    appointment_duration_minutes = Column(Integer, nullable=True, default=60)
    break_start = Column(String, nullable=True)  # "12:00"
    break_end = Column(String, nullable=True)  # "13:00"
    timezone = Column(String, nullable=True, default="America/New_York")
    notifications_enabled = Column(Boolean, default=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    users = relationship("User", back_populates="business")
    leads = relationship("Lead", back_populates="business")
