"""Tests for Stripe billing integration."""

import pytest
from unittest.mock import patch, MagicMock


@pytest.mark.asyncio
async def test_create_checkout_requires_business_id(client):
    """Checkout endpoint requires business_id parameter."""
    resp = await client.post("/api/v1/billing/create-checkout?success_url=https://example.com/success&cancel_url=https://example.com/cancel")
    # Missing business_id should return 422
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_stripe_webhook_signature_verification(client, db):
    """Stripe webhook should verify signature if secret is configured."""
    with patch("app.core.config.settings.STRIPE_WEBHOOK_SECRET", "test_secret"):
        resp = await client.post(
            "/api/v1/billing/webhook",
            json={"type": "customer.subscription.created"},
            headers={"stripe-signature": "invalid_signature"}
        )
        # Should fail signature verification
        assert resp.status_code == 400


@pytest.mark.asyncio
async def test_stripe_webhook_without_secret(client, db):
    """Stripe webhook should accept events without signature if secret is not set."""
    with patch("app.core.config.settings.STRIPE_WEBHOOK_SECRET", ""):
        resp = await client.post(
            "/api/v1/billing/webhook",
            json={
                "type": "customer.subscription.created",
                "data": {
                    "object": {
                        "id": "sub_123",
                        "customer": "cus_123",
                        "status": "active"
                    }
                }
            }
        )
        assert resp.status_code == 200


@pytest.mark.asyncio
async def test_subscription_created_updates_business(client, db):
    """subscription.created webhook should update business subscription_status."""
    from app.models.business import Business
    from sqlalchemy import select
    
    # Create a business with Stripe customer ID
    business = Business(
        name="Test Roofing",
        owner_phone="+15551234567",
        stripe_customer_id="cus_test123",
        subscription_status="inactive"
    )
    db.add(business)
    await db.commit()
    
    # Send subscription.created webhook
    with patch("app.core.config.settings.STRIPE_WEBHOOK_SECRET", ""):
        resp = await client.post(
            "/api/v1/billing/webhook",
            json={
                "type": "customer.subscription.created",
                "data": {
                    "object": {
                        "id": "sub_123",
                        "customer": "cus_test123",
                        "status": "active"
                    }
                }
            }
        )
    
    assert resp.status_code == 200
    
    # Verify business subscription_status updated
    result = await db.execute(select(Business).where(Business.stripe_customer_id == "cus_test123"))
    updated_business = result.scalar_one()
    assert updated_business.subscription_status == "active"


@pytest.mark.asyncio
async def test_subscription_deleted_cancels_subscription(client, db):
    """subscription.deleted webhook should cancel the subscription."""
    from app.models.business import Business
    from sqlalchemy import select
    
    # Create a business with active subscription
    business = Business(
        name="Test Plumbing",
        owner_phone="+15559999999",
        stripe_customer_id="cus_cancel123",
        subscription_status="active"
    )
    db.add(business)
    await db.commit()
    
    # Send subscription.deleted webhook
    with patch("app.core.config.settings.STRIPE_WEBHOOK_SECRET", ""):
        resp = await client.post(
            "/api/v1/billing/webhook",
            json={
                "type": "customer.subscription.deleted",
                "data": {
                    "object": {
                        "id": "sub_cancel123",
                        "customer": "cus_cancel123"
                    }
                }
            }
        )
    
    assert resp.status_code == 200
    
    # Verify business subscription_status updated to canceled
    result = await db.execute(select(Business).where(Business.stripe_customer_id == "cus_cancel123"))
    updated_business = result.scalar_one()
    assert updated_business.subscription_status == "canceled"
