from sqlalchemy import Column, String, Integer, Boolean, DateTime, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
import uuid

from app.core.database import Base


class SubscriptionPlan(Base):
    __tablename__ = "subscription_plans"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    name = Column(String, nullable=False)
    price_cents = Column(Integer, nullable=False)
    trial_days = Column(Integer, nullable=False, default=14)
    api_call_limit = Column(Integer, nullable=True)
    lead_limit = Column(Integer, nullable=True)
    appointment_limit = Column(Integer, nullable=True)
    features = Column(JSONB, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())

    # Relationships
    users = relationship("User", back_populates="plan")
