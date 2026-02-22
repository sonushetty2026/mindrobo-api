"""Business configuration model.

Each business (roofing contractor etc.) has config stored here:
owner phone, business name, Retell agent ID mapping, etc.
"""

from sqlalchemy import Column, String, DateTime, Boolean, Enum
from sqlalchemy.dialects.postgresql import UUID
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
    twilio_phone_number = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    
    # Stripe billing fields
    stripe_customer_id = Column(String, nullable=True)
    subscription_status = Column(
        Enum("active", "inactive", "trialing", "past_due", "canceled", name="subscription_status"),
        default="inactive",
        nullable=True
    )
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
