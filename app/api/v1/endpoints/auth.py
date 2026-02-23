"""Authentication endpoints for MindRobo."""

import logging
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.models.business import Business
from app.schemas.auth import (
    UserRegister,
    UserLogin,
    Token,
    UserOut,
    VerifyEmail,
    ForgotPassword,
    ResetPassword,
    ResendVerification,
    MessageResponse,
)
from app.services.auth import (
    hash_password,
    authenticate_user,
    create_access_token,
    get_user_by_email,
    generate_verification_token,
    generate_reset_token,
    get_user_by_verification_token,
    get_user_by_reset_token,
)
from app.services.email_service import email_service

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/register", response_model=MessageResponse, status_code=201)
async def register(user_data: UserRegister, db: AsyncSession = Depends(get_db)):
    """Register a new user and create their business.
    
    Creates both a Business and a User in a single transaction.
    Sends a verification email (stubbed — token logged to console).
    """
    # Check if user already exists
    existing_user = await get_user_by_email(db, user_data.email)
    if existing_user:
        raise HTTPException(status_code=409, detail="Email already registered")
    
    # Generate verification token
    verification_token, verification_expires = generate_verification_token()
    
    # Create the business
    business = Business(
        name=user_data.business_name,
        owner_email=user_data.email,
        owner_phone=user_data.owner_phone or "+10000000000",
        is_active=True,
    )
    db.add(business)
    await db.flush()  # Get business.id without committing
    
    # Create the user (unverified)
    user = User(
        email=user_data.email,
        hashed_password=hash_password(user_data.password),
        full_name=user_data.full_name,
        business_id=business.id,
        is_active=True,
        is_verified=False,
        verification_token=verification_token,
        verification_expires=verification_expires,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    
    # TODO: Send email via SendGrid (stubbed for now)
    logger.info(
        "🔐 VERIFICATION TOKEN for %s: %s (expires: %s)",
        user.email,
        verification_token,
        verification_expires,
    )
    
    logger.info("User registered (unverified): %s", user.email)
    
    return {
        "message": f"Registration successful. Please check your email to verify your account."
    }


@router.post("/login", response_model=Token)
async def login(credentials: UserLogin, db: AsyncSession = Depends(get_db)):
    """Login with email and password.
    
    Returns 403 if account is not verified.
    """
    from datetime import datetime
    
    user = await authenticate_user(db, credentials.email, credentials.password)
    
    if not user:
        raise HTTPException(
            status_code=401,
            detail="Incorrect email or password"
        )
    
    # Check if user is verified
    if not user.is_verified:
        raise HTTPException(
            status_code=403,
            detail="Please verify your email first"
        )
    
    # Update last login timestamp
    user.last_login_at = datetime.utcnow()
    await db.commit()
    
    # Include role in JWT payload
    access_token = create_access_token(data={
        "sub": str(user.id),
        "business_id": str(user.business_id),
        "role": user.role
    })
    
    logger.info("User logged in: %s (role: %s)", user.email, user.role)
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user_id": str(user.id),
        "business_id": str(user.business_id),
    }


@router.post("/verify-email", response_model=MessageResponse)
async def verify_email(data: VerifyEmail, db: AsyncSession = Depends(get_db)):
    """Verify email address using the verification token."""
    user = await get_user_by_verification_token(db, data.token)
    
    if not user:
        raise HTTPException(status_code=400, detail="Invalid or expired verification token")
    
    # Activate the account
    user.is_verified = True
    user.verification_token = None
    user.verification_expires = None
    await db.commit()
    
    logger.info("User verified: %s", user.email)
    
    # Send welcome email
    try:
        await email_service.send_welcome_email(user.email, user.full_name or user.email)
    except Exception as e:
        logger.error("Failed to send welcome email to %s: %s", user.email, e)

    return {"message": "Email verified successfully. You can now log in."}


@router.post("/forgot-password", response_model=MessageResponse)
async def forgot_password(data: ForgotPassword, db: AsyncSession = Depends(get_db)):
    """Request a password reset link.
    
    Generates a reset token and logs it to console (stubbed email).
    """
    user = await get_user_by_email(db, data.email)
    
    # Don't reveal if email exists or not (security best practice)
    if not user:
        logger.warning("Password reset requested for non-existent email: %s", data.email)
        return {"message": "If that email exists, a password reset link has been sent."}
    
    # Generate reset token
    reset_token, reset_expires = generate_reset_token()
    user.reset_token = reset_token
    user.reset_expires = reset_expires
    await db.commit()
    
    # TODO: Send email via SendGrid (stubbed for now)
    logger.info(
        "🔐 PASSWORD RESET TOKEN for %s: %s (expires: %s)",
        user.email,
        reset_token,
        reset_expires,
    )
    
    return {"message": "If that email exists, a password reset link has been sent."}


@router.post("/reset-password", response_model=MessageResponse)
async def reset_password(data: ResetPassword, db: AsyncSession = Depends(get_db)):
    """Reset password using the reset token."""
    user = await get_user_by_reset_token(db, data.token)
    
    if not user:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")
    
    # Update password and clear reset token
    user.hashed_password = hash_password(data.new_password)
    user.reset_token = None
    user.reset_expires = None
    await db.commit()
    
    logger.info("Password reset for user: %s", user.email)
    
    return {"message": "Password reset successfully. You can now log in."}


@router.post("/resend-verification", response_model=MessageResponse)
async def resend_verification(data: ResendVerification, db: AsyncSession = Depends(get_db)):
    """Resend verification email.
    
    Generates a new verification token and logs it to console (stubbed email).
    """
    user = await get_user_by_email(db, data.email)
    
    if not user:
        # Don't reveal if email exists
        return {"message": "If that email exists, a new verification link has been sent."}
    
    if user.is_verified:
        raise HTTPException(status_code=400, detail="Email is already verified")
    
    # Generate new verification token
    verification_token, verification_expires = generate_verification_token()
    user.verification_token = verification_token
    user.verification_expires = verification_expires
    await db.commit()
    
    # TODO: Send email via SendGrid (stubbed for now)
    logger.info(
        "🔐 NEW VERIFICATION TOKEN for %s: %s (expires: %s)",
        user.email,
        verification_token,
        verification_expires,
    )
    
    return {"message": "If that email exists, a new verification link has been sent."}


@router.get("/me", response_model=UserOut)
async def get_me(current_user: User = Depends(get_current_user)):
    """Get current authenticated user."""
    return current_user
