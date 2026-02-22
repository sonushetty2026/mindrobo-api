"""Tests for authentication endpoints."""

import pytest
from app.services.auth import hash_password, verify_password


def test_password_hashing():
    """Password hashing should be one-way and verifiable."""
    password = "supersecret123"
    hashed = hash_password(password)
    
    # Hashed password should be different from plain text
    assert hashed != password
    
    # Should verify correctly
    assert verify_password(password, hashed) is True
    
    # Wrong password should fail
    assert verify_password("wrongpassword", hashed) is False


@pytest.mark.asyncio
async def test_register_creates_user_and_business(client, db):
    """Registration should create both a user and a business."""
    resp = await client.post("/api/v1/auth/register", json={
        "email": "test@example.com",
        "password": "testpass123",
        "full_name": "Test User",
        "business_name": "Test Roofing Co"
    })
    
    assert resp.status_code == 201
    data = resp.json()
    assert "access_token" in data
    assert "business_id" in data
    assert "user_id" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_register_duplicate_email_fails(client, db):
    """Registering the same email twice should fail."""
    user_data = {
        "email": "duplicate@example.com",
        "password": "testpass123",
        "business_name": "First Business"
    }
    
    # First registration succeeds
    resp1 = await client.post("/api/v1/auth/register", json=user_data)
    assert resp1.status_code == 201
    
    # Second registration fails
    resp2 = await client.post("/api/v1/auth/register", json=user_data)
    assert resp2.status_code == 400
    assert "already registered" in resp2.json()["detail"].lower()


@pytest.mark.asyncio
async def test_login_with_valid_credentials(client, db):
    """Login should return a token for valid credentials."""
    # Register first
    await client.post("/api/v1/auth/register", json={
        "email": "login@example.com",
        "password": "mypassword",
        "business_name": "My Business"
    })
    
    # Login
    resp = await client.post("/api/v1/auth/login", json={
        "email": "login@example.com",
        "password": "mypassword"
    })
    
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_with_invalid_credentials(client, db):
    """Login should fail with wrong password."""
    # Register first
    await client.post("/api/v1/auth/register", json={
        "email": "fail@example.com",
        "password": "correctpass",
        "business_name": "Test Business"
    })
    
    # Login with wrong password
    resp = await client.post("/api/v1/auth/login", json={
        "email": "fail@example.com",
        "password": "wrongpass"
    })
    
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_protected_endpoint_requires_auth(client, db):
    """Protected endpoints should reject requests without a token."""
    # Test a truly protected endpoint (/me requires auth, while /calls/ has optional auth)
    resp = await client.get("/api/v1/businesses/me")
    # HTTPBearer can return 400 (missing header) or 403 depending on implementation
    assert resp.status_code in [400, 403]


@pytest.mark.asyncio
async def test_protected_endpoint_with_valid_token(client, db):
    """Protected endpoints should work with a valid token."""
    # Register and get token
    register_resp = await client.post("/api/v1/auth/register", json={
        "email": "protected@example.com",
        "password": "testpass",
        "business_name": "Protected Test Co"
    })
    token = register_resp.json()["access_token"]
    
    # Access protected endpoint - should return user's business
    resp = await client.get(
        "/api/v1/businesses/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "Protected Test Co"
