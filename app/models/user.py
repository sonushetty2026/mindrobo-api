"""User model for multi-tenant authentication."""

from sqlalchemy import Column, String, DateTime, ForeignKey, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime
from app.core.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    business_id = Column(UUID(as_uuid=True), ForeignKey("businesses.id"), nullable=False, index=True)
    full_name = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    verification_token = Column(String, nullable=True, index=True)
    verification_expires = Column(DateTime, nullable=True)
    reset_token = Column(String, nullable=True, index=True)
    reset_expires = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Phase 3 fields
    role = Column(String, nullable=False, default="user")
    is_trial = Column(Boolean, nullable=False, default=True)
    trial_ends_at = Column(DateTime, nullable=True)
    is_paused = Column(Boolean, nullable=False, default=False)
    paused_at = Column(DateTime, nullable=True)
    plan_id = Column(UUID(as_uuid=True), ForeignKey("subscription_plans.id"), nullable=True)
    fcm_token = Column(String, nullable=True)
    last_login_at = Column(DateTime, nullable=True)
    
    # Relationships
    business = relationship("Business", back_populates="users")
    plan = relationship("SubscriptionPlan", back_populates="users")
    notifications = relationship("Notification", back_populates="user")
    api_usage_logs = relationship("APIUsageLog", back_populates="user")
    admin_actions = relationship("AdminAuditLog", foreign_keys="AdminAuditLog.admin_id", back_populates="admin")
    audit_logs_as_target = relationship("AdminAuditLog", foreign_keys="AdminAuditLog.target_user_id", back_populates="target_user")
