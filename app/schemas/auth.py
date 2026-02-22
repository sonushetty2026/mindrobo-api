"""Pydantic schemas for authentication endpoints."""

from pydantic import BaseModel, EmailStr
from uuid import UUID


class UserRegister(BaseModel):
    """Request schema for user registration."""
    email: EmailStr
    password: str
    full_name: str | None = None
    business_name: str
    owner_name: str | None = None
    owner_phone: str | None = None


class UserLogin(BaseModel):
    """Request schema for user login."""
    email: EmailStr
    password: str


class Token(BaseModel):
    """Response schema for login — returns JWT token."""
    access_token: str
    token_type: str = "bearer"
    business_id: UUID | None = None
    user_id: UUID | None = None


class TokenData(BaseModel):
    """Decoded token data."""
    user_id: UUID | None = None
    business_id: UUID | None = None


class UserOut(BaseModel):
    """Response schema for user info."""
    id: UUID
    email: str
    full_name: str | None = None
    business_id: UUID
    is_active: bool

    class Config:
        from_attributes = True
