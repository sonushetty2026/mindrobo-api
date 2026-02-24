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
    onboarding_complete: bool = False
    role: str | None = None
    full_name: str | None = None
    email: str | None = None


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
    is_verified: bool

    class Config:
        from_attributes = True


class VerifyEmail(BaseModel):
    """Request schema for email verification."""
    token: str


class ForgotPassword(BaseModel):
    """Request schema for forgot password."""
    email: EmailStr


class ResetPassword(BaseModel):
    """Request schema for password reset."""
    token: str
    new_password: str


class ResendVerification(BaseModel):
    """Request schema for resending verification email."""
    email: EmailStr


class MessageResponse(BaseModel):
    """Generic success message response."""
    message: str
