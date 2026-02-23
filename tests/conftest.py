"""Shared test fixtures for MindRobo API tests.

Uses an in-memory SQLite async engine so tests run without PostgreSQL.
"""

import asyncio
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.core.database import Base, get_db
from app.main import app

# Import all models to ensure they're registered with Base.metadata
from app.models.business import Business
from app.models.call import Call
from app.models.user import User


# Use aiosqlite for fast, isolated tests
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

engine = create_async_engine(TEST_DATABASE_URL, echo=False)
TestSession = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    """Create all tables before each test, drop after."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


async def override_get_db():
    async with TestSession() as session:
        yield session


app.dependency_overrides[get_db] = override_get_db


@pytest_asyncio.fixture
async def client():
    """Async HTTP test client."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture
async def db():
    """Direct DB session for test setup/assertions."""
    async with TestSession() as session:
        yield session


@pytest_asyncio.fixture
async def verified_user(client, db):
    """Create a verified user and return their auth token."""
    from app.models.user import User
    from app.models.business import Business
    from app.services.auth import hash_password
    
    # Create business
    business = Business(
        name="Test Business",
        owner_email="verified@example.com",
        owner_phone="+10000000000",
        is_active=True,
    )
    db.add(business)
    await db.flush()
    
    # Create pre-verified user
    user = User(
        email="verified@example.com",
        hashed_password=hash_password("testpass123"),
        full_name="Verified User",
        business_id=business.id,
        is_active=True,
        is_verified=True,
    )
    db.add(user)
    await db.commit()
    
    # Login to get token
    resp = await client.post("/api/v1/auth/login", json={
        "email": "verified@example.com",
        "password": "testpass123"
    })
    
    return {
        "token": resp.json()["access_token"],
        "user_id": str(user.id),
        "business_id": str(business.id),
        "email": "verified@example.com",
    }
