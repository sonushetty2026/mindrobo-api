"""Business configuration model.

Each business (roofing contractor etc.) has config stored here:
owner phone, business name, Retell agent ID mapping, etc.
"""

from sqlalchemy import Column, String, DateTime, Boolean, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.types import JSON
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime
from app.core.database import Base


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
    
    # Onboarding/config fields (use JSON for SQLite compatibility, will be JSONB in Postgres)
    industry = Column(String, nullable=True)
    hours_of_operation = Column(JSON, nullable=True)  # {"mon": "9-5", "tue": "9-5", ...}
    greeting_script = Column(Text, nullable=True)
    faqs = Column(JSON, nullable=True)  # [{"question": "...", "answer": "..."}, ...]
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    users = relationship("User", back_populates="business")
