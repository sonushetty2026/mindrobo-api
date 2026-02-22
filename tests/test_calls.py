"""Tests for calls list/detail endpoints."""

import pytest
from unittest.mock import patch, AsyncMock
from app.models.call import Call


@pytest.mark.asyncio
async def test_list_calls_empty(client):
    resp = await client.get("/api/v1/calls/")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_get_call_not_found(client):
    resp = await client.get("/api/v1/calls/nonexistent")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_list_calls_after_webhook(client):
    """After a call_ended webhook, the call should appear in the list."""
    with patch("app.services.calls.send_caller_confirmation", new_callable=AsyncMock), \
         patch("app.services.calls.send_owner_summary", new_callable=AsyncMock), \
         patch("app.api.v1.endpoints.webhooks.broadcast", new_callable=AsyncMock):

        await client.post("/api/v1/webhooks/retell", json={
            "event": "call_ended",
            "data": {
                "call_id": "list-test-call",
                "from_number": "+15550000000",
                "agent_id": "agent-1",
            }
        })

    resp = await client.get("/api/v1/calls/")
    assert resp.status_code == 200
    calls = resp.json()
    assert len(calls) == 1
    assert calls[0]["call_id"] == "list-test-call"
