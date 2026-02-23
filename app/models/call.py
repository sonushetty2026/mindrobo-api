from sqlalchemy import Column, String, DateTime, Text, Enum, Integer
from sqlalchemy.dialects.postgresql import UUID
import uuid
from datetime import datetime
from app.core.database import Base

class Call(Base):
    __tablename__ = "calls"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    call_id = Column(String, unique=True, index=True)   # Retell call ID
    caller_phone = Column(String)
    business_id = Column(String, index=True)
    status = Column(Enum("active","completed","failed", name="call_status"), default="active")
    outcome = Column(Enum("callback_scheduled","lead_captured","escalated","voicemail", name="call_outcome"), nullable=True)
    approval_status = Column(Enum("pending","approved","rejected", name="approval_status"), default="pending", nullable=True)
    transcript = Column(Text, nullable=True)
    summary = Column(Text, nullable=True)
    lead_name = Column(String, nullable=True)
    lead_address = Column(String, nullable=True)
    service_type = Column(String, nullable=True)
    urgency = Column(String, nullable=True)
    
    # Recording and transcript storage
    recording_url = Column(String, nullable=True)  # Azure Blob URL
    transcript_url = Column(String, nullable=True)  # Azure Blob URL
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
