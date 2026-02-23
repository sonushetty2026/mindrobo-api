"""Tests for authentication endpoints."""

import pytest
from app.services.auth import hash_password, verify_password
from app.models.user import User
from sqlalchemy import select


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
    """Registration should create both a user and a business (unverified)."""
    resp = await client.post("/api/v1/auth/register", json={
        "email": "test@example.com",
        "password": "testpass123",
        "full_name": "Test User",
        "business_name": "Test Roofing Co"
    })
    
    assert resp.status_code == 201
    data = resp.json()
    assert "message" in data
    assert "verify" in data["message"].lower()
    
    # Check user exists in DB (unverified)
    result = await db.execute(select(User).where(User.email == "test@example.com"))
    user = result.scalar_one_or_none()
    assert user is not None
    assert user.is_verified is False
    assert user.verification_token is not None


@pytest.mark.asyncio
async def test_register_duplicate_email_fails(client, db):
    """Registering the same email twice should fail with 409."""
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
    assert resp2.status_code == 409
    assert "already registered" in resp2.json()["detail"].lower()


@pytest.mark.asyncio
async def test_login_with_unverified_account_fails(client, db):
    """Login should return 403 for unverified accounts."""
    # Register (unverified)
    await client.post("/api/v1/auth/register", json={
        "email": "unverified@example.com",
        "password": "mypassword",
        "business_name": "My Business"
    })
    
    # Try to login
    resp = await client.post("/api/v1/auth/login", json={
        "email": "unverified@example.com",
        "password": "mypassword"
    })
    
    assert resp.status_code == 403
    assert "verify" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_verify_email_activates_account(client, db):
    """Email verification should activate the account."""
    # Register
    await client.post("/api/v1/auth/register", json={
        "email": "verify@example.com",
        "password": "testpass",
        "business_name": "Verify Business"
    })
    
    # Get verification token from DB
    result = await db.execute(select(User).where(User.email == "verify@example.com"))
    user = result.scalar_one()
    token = user.verification_token
    
    # Verify email
    resp = await client.post("/api/v1/auth/verify-email", json={"token": token})
    assert resp.status_code == 200
    assert "verified" in resp.json()["message"].lower()
    
    # Check user is now verified
    await db.refresh(user)
    assert user.is_verified is True
    assert user.verification_token is None


@pytest.mark.asyncio
async def test_login_with_verified_account(client, db, verified_user):
    """Login should return a token for verified accounts."""
    resp = await client.post("/api/v1/auth/login", json={
        "email": verified_user["email"],
        "password": "testpass123"
    })
    
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert "user_id" in data
    assert "business_id" in data


@pytest.mark.asyncio
async def test_login_with_invalid_credentials(client, db, verified_user):
    """Login should fail with wrong password."""
    resp = await client.post("/api/v1/auth/login", json={
        "email": verified_user["email"],
        "password": "wrongpass"
    })
    
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_forgot_password_generates_reset_token(client, db, verified_user):
    """Forgot password should generate a reset token."""
    resp = await client.post("/api/v1/auth/forgot-password", json={
        "email": verified_user["email"]
    })
    
    assert resp.status_code == 200
    assert "message" in resp.json()
    
    # Check reset token was generated
    result = await db.execute(select(User).where(User.email == verified_user["email"]))
    user = result.scalar_one()
    assert user.reset_token is not None
    assert user.reset_expires is not None


@pytest.mark.asyncio
async def test_reset_password_changes_password(client, db, verified_user):
    """Password reset should update the password."""
    # Request reset
    await client.post("/api/v1/auth/forgot-password", json={
        "email": verified_user["email"]
    })
    
    # Get reset token from DB
    result = await db.execute(select(User).where(User.email == verified_user["email"]))
    user = result.scalar_one()
    token = user.reset_token
    
    # Reset password
    new_password = "newpassword123"
    resp = await client.post("/api/v1/auth/reset-password", json={
        "token": token,
        "new_password": new_password
    })
    
    assert resp.status_code == 200
    assert "reset" in resp.json()["message"].lower()
    
    # Old password should not work
    resp = await client.post("/api/v1/auth/login", json={
        "email": verified_user["email"],
        "password": "testpass123"
    })
    assert resp.status_code == 401
    
    # New password should work
    resp = await client.post("/api/v1/auth/login", json={
        "email": verified_user["email"],
        "password": new_password
    })
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_resend_verification_generates_new_token(client, db):
    """Resend verification should generate a new token."""
    # Register
    await client.post("/api/v1/auth/register", json={
        "email": "resend@example.com",
        "password": "testpass",
        "business_name": "Resend Business"
    })
    
    # Get old token
    result = await db.execute(select(User).where(User.email == "resend@example.com"))
    user = result.scalar_one()
    old_token = user.verification_token
    
    # Resend verification
    resp = await client.post("/api/v1/auth/resend-verification", json={
        "email": "resend@example.com"
    })
    
    assert resp.status_code == 200
    
    # Check new token was generated
    await db.refresh(user)
    assert user.verification_token != old_token


@pytest.mark.asyncio
async def test_resend_verification_fails_for_verified_account(client, db, verified_user):
    """Resend verification should fail for already verified accounts."""
    resp = await client.post("/api/v1/auth/resend-verification", json={
        "email": verified_user["email"]
    })
    
    assert resp.status_code == 400
    assert "already verified" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_protected_endpoint_requires_auth(client, db):
    """Protected endpoints should reject requests without a token."""
    resp = await client.get("/api/v1/auth/me")
    # HTTPBearer can return 403 (missing header) or 401 depending on implementation
    assert resp.status_code in [401, 403]


@pytest.mark.asyncio
async def test_protected_endpoint_with_valid_token(client, db, verified_user):
    """Protected endpoints should work with a valid token."""
    resp = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {verified_user['token']}"}
    )
    
    assert resp.status_code == 200
    data = resp.json()
    assert data["email"] == verified_user["email"]
    assert data["is_verified"] is True
