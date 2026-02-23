"""Lead model for MindRobo."""
import enum
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, DateTime, Enum, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.core.database import Base


class LeadSource(str, enum.Enum):
    """Lead source enum."""
    CALL = "call"
    WEB = "web"
    MANUAL = "manual"


class LeadStatus(str, enum.Enum):
    """Lead status enum."""
    NEW = "new"
    CONTACTED = "contacted"
    CONVERTED = "converted"
    LOST = "lost"


class Lead(Base):
    """Lead model."""
    __tablename__ = "leads"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    business_id = Column(UUID(as_uuid=True), ForeignKey("businesses.id"), nullable=False, index=True)
    caller_name = Column(String(255), nullable=False)
    caller_phone = Column(String(50), nullable=False)
    caller_email = Column(String(255), nullable=True)
    service_needed = Column(String(500), nullable=True)
    notes = Column(Text, nullable=True)
    source = Column(Enum(LeadSource), nullable=False, default=LeadSource.MANUAL)
    status = Column(Enum(LeadStatus), nullable=False, default=LeadStatus.NEW, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    business = relationship("Business", back_populates="leads")
