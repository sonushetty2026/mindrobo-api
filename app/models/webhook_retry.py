"""Webhook retry queue model."""

from sqlalchemy import Column, String, Integer, Text, DateTime
from sqlalchemy.dialects.postgresql import UUID, JSONB
import uuid
from datetime import datetime
from app.core.database import Base


class WebhookRetry(Base):
    __tablename__ = "webhook_retries"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    service = Column(String, nullable=False, index=True)  # 'retell' or 'twilio'
    payload = Column(JSONB, nullable=False)  # Original webhook payload
    attempts = Column(Integer, nullable=False, default=0)
    last_error = Column(Text, nullable=True)
    status = Column(String, nullable=False, default="pending", index=True)  # pending, retrying, failed, success
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
