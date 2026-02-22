"""Tests for business onboarding endpoints."""

import pytest


@pytest.mark.asyncio
async def test_onboard_business_success(client):
    """Should successfully onboard a new business."""
    resp = await client.post("/api/v1/onboarding/onboard", json={
        "business_name": "Joe's Plumbing",
        "owner_phone": "+15551234567",
        "industry": "Plumbing",
        "hours_of_operation": {"mon": "9-5", "tue": "9-5"},
        "greeting_script": "Thanks for calling Joe's Plumbing!",
        "faqs": [
            {"question": "Do you offer emergency service?", "answer": "Yes, 24/7"},
            {"question": "What areas do you serve?", "answer": "All of Seattle"}
        ]
    })
    
    assert resp.status_code == 201
    data = resp.json()
    assert "business_id" in data
    assert data["business_name"] == "Joe's Plumbing"
    assert "agent_config_url" in data


@pytest.mark.asyncio
async def test_onboard_business_invalid_phone(client):
    """Should reject invalid phone number."""
    resp = await client.post("/api/v1/onboarding/onboard", json={
        "business_name": "Test Business",
        "owner_phone": "abc123",
        "industry": "Testing"
    })
    
    assert resp.status_code == 422  # Validation error


@pytest.mark.asyncio
async def test_onboard_business_minimal(client):
    """Should onboard with just required fields."""
    resp = await client.post("/api/v1/onboarding/onboard", json={
        "business_name": "Minimal Business",
        "owner_phone": "5551112222",
        "industry": "General"
    })
    
    assert resp.status_code == 201
    data = resp.json()
    assert data["business_name"] == "Minimal Business"


@pytest.mark.asyncio
async def test_get_agent_config(client, db):
    """Should return agent config for a business."""
    # First onboard
    resp1 = await client.post("/api/v1/onboarding/onboard", json={
        "business_name": "Config Test Business",
        "owner_phone": "+15559998888",
        "industry": "Roofing",
        "greeting_script": "Custom greeting!"
    })
    business_id = resp1.json()["business_id"]
    
    # Get config
    resp2 = await client.get(f"/api/v1/onboarding/{business_id}/config")
    
    assert resp2.status_code == 200
    config = resp2.json()
    assert config["business_name"] == "Config Test Business"
    assert config["industry"] == "Roofing"
    assert config["greeting_script"] == "Custom greeting!"


@pytest.mark.asyncio
async def test_get_agent_config_not_found(client):
    """Should return 404 for nonexistent business."""
    resp = await client.get("/api/v1/onboarding/00000000-0000-0000-0000-000000000000/config")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_update_agent_config(client):
    """Should update agent config fields."""
    # Onboard
    resp1 = await client.post("/api/v1/onboarding/onboard", json={
        "business_name": "Update Test",
        "owner_phone": "5557778888",
        "industry": "HVAC"
    })
    business_id = resp1.json()["business_id"]
    
    # Update config
    resp2 = await client.put(f"/api/v1/onboarding/{business_id}/config", json={
        "greeting_script": "New greeting!",
        "faqs": [{"question": "Updated?", "answer": "Yes"}]
    })
    
    assert resp2.status_code == 200
    data = resp2.json()
    assert "updated_fields" in data
    
    # Verify update
    resp3 = await client.get(f"/api/v1/onboarding/{business_id}/config")
    config = resp3.json()
    assert config["greeting_script"] == "New greeting!"
    assert len(config["faqs"]) == 1


@pytest.mark.asyncio
async def test_test_call_simulation(client):
    """Should return realistic greeting for test call."""
    # Onboard
    resp1 = await client.post("/api/v1/onboarding/onboard", json={
        "business_name": "Test Call Co",
        "owner_phone": "5556667777",
        "industry": "Testing",
        "greeting_script": "Hello from Test Call Co!",
        "hours_of_operation": {"mon": "9-5"},
        "faqs": [
            {"question": "FAQ 1?", "answer": "Answer 1"},
            {"question": "FAQ 2?", "answer": "Answer 2"}
        ]
    })
    business_id = resp1.json()["business_id"]
    
    # Test call
    resp2 = await client.post(f"/api/v1/onboarding/{business_id}/test-call")
    
    assert resp2.status_code == 200
    data = resp2.json()
    assert data["greeting"] == "Hello from Test Call Co!"
    assert data["business_name"] == "Test Call Co"
    assert data["hours"] is not None
    assert len(data["sample_faqs"]) == 2


@pytest.mark.asyncio
async def test_test_call_default_greeting(client):
    """Should use default greeting if custom script not provided."""
    # Onboard without greeting_script
    resp1 = await client.post("/api/v1/onboarding/onboard", json={
        "business_name": "Default Greeting Business",
        "owner_phone": "5554443333",
        "industry": "Services"
    })
    business_id = resp1.json()["business_id"]
    
    # Test call
    resp2 = await client.post(f"/api/v1/onboarding/{business_id}/test-call")
    
    assert resp2.status_code == 200
    data = resp2.json()
    assert "Default Greeting Business" in data["greeting"]
    assert "How can I help you today?" in data["greeting"]
