"""Authentication endpoints for MindRobo."""

import logging
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.models.business import Business
from app.schemas.auth import UserRegister, UserLogin, Token, UserOut
from app.services.auth import (
    hash_password,
    authenticate_user,
    create_access_token,
    get_user_by_email,
)

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/register", response_model=Token, status_code=201)
async def register(user_data: UserRegister, db: AsyncSession = Depends(get_db)):
    """Register a new user and create their business.
    
    Creates both a Business and a User in a single transaction.
    Returns a JWT token for immediate login.
    """
    # Check if user already exists
    existing_user = await get_user_by_email(db, user_data.email)
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Create the business
    business = Business(
        name=user_data.business_name,
        owner_email=user_data.email,
        owner_phone=getattr(user_data, 'owner_phone', ""),
        is_active=True,
    )
    db.add(business)
    await db.flush()  # Get business.id without committing
    
    # Create the user
    user = User(
        email=user_data.email,
        hashed_password=hash_password(user_data.password),
        full_name=getattr(user_data, 'full_name', None),
        business_id=business.id,
        is_active=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    
    # Generate JWT
    access_token = create_access_token(data={
        "sub": str(user.id),
        "business_id": str(user.business_id)
    })
    
    logger.info("User registered: %s", user.email)
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user_id": str(user.id),
        "business_id": str(user.business_id)
    }


@router.post("/login", response_model=Token)
async def login(credentials: UserLogin, db: AsyncSession = Depends(get_db)):
    """Login with email and password."""
    user = await authenticate_user(db, credentials.email, credentials.password)
    
    if not user:
        raise HTTPException(
            status_code=401,
            detail="Incorrect email or password"
        )
    
    access_token = create_access_token(data={
        "sub": str(user.id),
        "business_id": str(user.business_id)
    })
    
    logger.info("User logged in: %s", user.email)
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me", response_model=UserOut)
async def get_me(current_user: User = Depends(get_current_user)):
    """Get current authenticated user."""
    return current_user
