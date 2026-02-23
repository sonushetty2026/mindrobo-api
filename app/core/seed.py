"""Seed test account on app startup."""

import logging
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import async_session
from app.models.user import User
from app.models.business import Business
from app.services.auth import hash_password, get_user_by_email

logger = logging.getLogger(__name__)

TEST_EMAIL = "sonushetty2026@gmail.com"
TEST_PASSWORD = "TestMindRobo2026!"
TEST_BUSINESS_NAME = "MindRobo Test Business"


async def seed_test_account():
    """Create a pre-verified test account on startup if it doesn't exist."""
    async with async_session() as db:
        try:
            # Check if test account already exists
            existing_user = await get_user_by_email(db, TEST_EMAIL)
            
            if existing_user:
                logger.info(f"✅ Test account already exists: {TEST_EMAIL}")
                return
            
            # Create test business
            business = Business(
                name=TEST_BUSINESS_NAME,
                owner_email=TEST_EMAIL,
                owner_phone="+10000000000",
                is_active=True,
            )
            db.add(business)
            await db.flush()
            
            # Create pre-verified test user
            user = User(
                email=TEST_EMAIL,
                hashed_password=hash_password(TEST_PASSWORD),
                full_name="Test User",
                business_id=business.id,
                is_active=True,
                is_verified=True,  # Pre-verified
                verification_token=None,
                verification_expires=None,
            )
            db.add(user)
            await db.commit()
            
            logger.info(f"✅ Test account created: {TEST_EMAIL} (pre-verified)")
            
        except Exception as e:
            logger.error(f"Failed to seed test account: {e}")
            await db.rollback()
