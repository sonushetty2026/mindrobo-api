"""Authentication endpoints for MindRobo."""

import logging
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, Depends, Request
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
from app.services.notification_service import create_welcome_notification

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
    
    # Create the user (unverified) with trial settings
    trial_ends_at = datetime.utcnow() + timedelta(days=14)
    user = User(
        email=user_data.email,
        hashed_password=hash_password(user_data.password),
        full_name=user_data.full_name,
        business_id=business.id,
        is_active=True,
        is_verified=False,
        verification_token=verification_token,
        verification_expires=verification_expires,
        is_trial=True,
        trial_ends_at=trial_ends_at,
        is_paused=False,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    
    # Create welcome notification
    await create_welcome_notification(db, user.id)
    
    # Send verification email via SendGrid
    logger.info(
        "🔐 VERIFICATION TOKEN for %s: %s (expires: %s)",
        user.email,
        verification_token,
        verification_expires,
    )

    # Build verification URL
    verify_url = f"http://52.159.104.87:8000/verify-email?token={verification_token}"
    try:
        await email_service.send_email(
            to=user.email,
            subject="Verify your MindRobo account",
            html_body=f"""
            <html>
                <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                    <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                        <h2 style="color: #4A90E2;">Welcome to MindRobo!</h2>
                        <p>Hi {user.full_name or user.email},</p>
                        <p>Thank you for signing up! Please verify your email to get started.</p>
                        <p>
                            <a href="{verify_url}"
                               style="display: inline-block; padding: 12px 24px; background-color: #4A90E2;
                                      color: white; text-decoration: none; border-radius: 5px; margin: 20px 0;">
                                Verify My Email
                            </a>
                        </p>
                        <p style="color: #666; font-size: 14px;">Or copy and paste this link: {verify_url}</p>
                        <p style="color: #666; font-size: 14px; margin-top: 40px;">
                            This link expires in 24 hours.<br>
                            If you didn't create this account, you can safely ignore this email.
                        </p>
                    </div>
                </body>
            </html>
            """,
            plain_body=f"Welcome to MindRobo!\n\nVerify your email: {verify_url}\n\nThis link expires in 24 hours.",
        )
    except Exception as e:
        logger.error("Failed to send verification email to %s: %s", user.email, e)
    
    logger.info("User registered (unverified): %s", user.email)
    
    return {
        "message": f"Registration successful. Please check your email to verify your account."
    }


@router.post("/login", response_model=Token)
async def login(credentials: UserLogin, request: Request, db: AsyncSession = Depends(get_db)):
    """Login with email and password.
    
    Returns 403 if account is not verified.
    Issue #101: Brute force protection - max 5 failed attempts per 15 min.
    """
    from datetime import datetime
    from fastapi import Request
    from app.services.security_service import check_rate_limit, record_failed_login, clear_failed_attempts
    
    # Check if IP is rate limited (brute force protection)
    rate_limit_error = check_rate_limit(request)
    if rate_limit_error:
        raise rate_limit_error
    
    user = await authenticate_user(db, credentials.email, credentials.password)
    
    if not user:
        # Record failed login attempt
        record_failed_login(request, credentials.email)
        
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
    
    # Successful login - clear failed attempts for this IP
    clear_failed_attempts(request)
    
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
    
    # Send password reset email via SendGrid
    reset_link = f"http://52.159.104.87:8000/reset-password?token={reset_token}"
    logger.info("PASSWORD RESET TOKEN for %s: %s", user.email, reset_token)
    try:
        await email_service.send_email(
            to=user.email,
            subject="Reset your MindRobo password",
            html_body=(
                f'<html><body style="font-family:Arial,sans-serif;color:#333;">'  
                f'<div style="max-width:600px;margin:0 auto;padding:20px;">'  
                f'<h2 style="color:#4A90E2;">Reset Your Password</h2>'  
                f'<p>Hi {user.full_name or user.email},</p>'  
                f'<p>We received a request to reset your MindRobo password. '
                f'Click the button below to set a new password. This link expires in 24 hours.</p>'
                f'<a href="{reset_link}" style="display:inline-block;padding:12px 24px;'
                f'background:#4A90E2;color:white;text-decoration:none;border-radius:5px;margin:20px 0;">'
                f'Reset Password</a>'
                f'<p>If you did not request this, ignore this email.</p>'
                f'<p>Best regards,<br>The MindRobo Team</p>'
                f'</div></body></html>'
            ),
            plain_body=f"Reset your MindRobo password:\n{reset_link}\n\nExpires in 24 hours. Ignore if you did not request this."
        )
        logger.info("Password reset email sent to %s", user.email)
    except Exception as e:
        logger.error("Failed to send password reset email to %s: %s", user.email, e)

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
