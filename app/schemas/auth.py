"""Pydantic schemas for authentication."""

from pydantic import BaseModel, EmailStr
from uuid import UUID


class UserRegister(BaseModel):
    """Registration request schema."""
    email: EmailStr
    password: str
    business_name: str
    owner_name: str | None = None
    owner_phone: str


class UserLogin(BaseModel):
    """Login request schema."""
    email: EmailStr
    password: str


class Token(BaseModel):
    """JWT token response schema."""
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    """Decoded token data."""
    user_id: UUID | None = None
    business_id: UUID | None = None


class UserOut(BaseModel):
    """User response schema."""
    id: UUID
    email: str
    business_id: UUID
    is_active: bool
    
    class Config:
        from_attributes = True
