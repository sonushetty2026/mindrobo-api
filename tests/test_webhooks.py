"""Tests for the Retell webhook endpoint."""

import pytest


@pytest.mark.asyncio
async def test_call_started_ack(client):
    resp = await client.post("/api/v1/webhooks/retell", json={
        "event": "call_started",
        "data": {"call_id": "test-call-1"}
    })
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_call_ended_saves_to_db(client):
    """call_ended should save a Call record and return outcome."""
    resp = await client.post("/api/v1/webhooks/retell", json={
        "event": "call_ended",
        "data": {
            "call_id": "test-call-ended-1",
            "from_number": "+15551234567",
            "agent_id": "agent-xyz",
            "transcript": "Hi, I need roof repair.",
            "call_analysis": {
                "call_summary": "Caller needs roof repair after storm damage.",
                "custom_analysis_data": {
                    "caller_name": "John Doe",
                    "address": "123 Main St",
                    "service_type": "roof repair",
                    "urgency": "high"
                }
            }
        }
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["call_id"] == "test-call-ended-1"
    assert data["outcome"] == "lead_captured"


@pytest.mark.asyncio
async def test_call_ended_missing_call_id(client):
    resp = await client.post("/api/v1/webhooks/retell", json={
        "event": "call_ended",
        "data": {}
    })
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_call_ended_minimal_data(client):
    """call_ended with no analysis → callback_scheduled outcome."""
    resp = await client.post("/api/v1/webhooks/retell", json={
        "event": "call_ended",
        "data": {
            "call_id": "test-call-minimal",
            "from_number": "+15559999999",
        }
    })
    assert resp.status_code == 200
    assert resp.json()["outcome"] == "callback_scheduled"


@pytest.mark.asyncio
async def test_unknown_event_ok(client):
    resp = await client.post("/api/v1/webhooks/retell", json={
        "event": "some_future_event",
        "data": {}
    })
    assert resp.status_code == 200
