"""Tests for Retell webhook endpoint."""

import pytest
from unittest.mock import patch, AsyncMock


@pytest.mark.asyncio
async def test_call_started_ack(client):
    """call_started should return 200 with ack."""
    resp = await client.post("/api/v1/webhooks/retell", json={
        "event": "call_started",
        "data": {"call_id": "test-call-1"}
    })
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_call_ended_saves_to_db(client, db):
    """call_ended should save a call record to the database."""
    with patch("app.api.v1.endpoints.webhooks.send_caller_confirmation", new_callable=AsyncMock) as mock_sms_caller, \
         patch("app.api.v1.endpoints.webhooks.send_owner_summary", new_callable=AsyncMock) as mock_sms_owner, \
         patch("app.api.v1.endpoints.webhooks.broadcast", new_callable=AsyncMock):

        resp = await client.post("/api/v1/webhooks/retell", json={
            "event": "call_ended",
            "data": {
                "call_id": "test-call-100",
                "from_number": "+15551234567",
                "agent_id": "agent-abc",
                "transcript": "Hi I need roof repair",
                "call_analysis": {
                    "call_summary": "Caller needs roof repair after storm damage",
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
        assert data["call_id"] == "test-call-100"
        assert data["outcome"] == "lead_captured"

    # Verify it's in the DB
    resp2 = await client.get("/api/v1/calls/test-call-100")
    assert resp2.status_code == 200
    call = resp2.json()
    assert call["lead_name"] == "John Doe"
    assert call["service_type"] == "roof repair"
    assert call["urgency"] == "high"


@pytest.mark.asyncio
async def test_call_ended_missing_call_id(client):
    """call_ended without call_id should return 400."""
    resp = await client.post("/api/v1/webhooks/retell", json={
        "event": "call_ended",
        "data": {}
    })
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_call_ended_triggers_caller_sms(client):
    """call_ended should attempt to send SMS to caller."""
    with patch("app.api.v1.endpoints.webhooks.send_caller_confirmation", new_callable=AsyncMock) as mock_sms, \
         patch("app.api.v1.endpoints.webhooks.send_owner_summary", new_callable=AsyncMock), \
         patch("app.api.v1.endpoints.webhooks.broadcast", new_callable=AsyncMock):

        await client.post("/api/v1/webhooks/retell", json={
            "event": "call_ended",
            "data": {
                "call_id": "test-call-sms",
                "from_number": "+15559999999",
                "agent_id": "agent-xyz",
            }
        })
        mock_sms.assert_called_once_with("+15559999999", "our team")
