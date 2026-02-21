"""Tests for the calls list/detail endpoints."""

import pytest


@pytest.mark.asyncio
async def test_list_calls_empty(client):
    resp = await client.get("/api/v1/calls/")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_get_call_not_found(client):
    resp = await client.get("/api/v1/calls/nonexistent-id")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_list_calls_after_webhook(client):
    """Create a call via webhook, then verify it shows in the list."""
    await client.post("/api/v1/webhooks/retell", json={
        "event": "call_ended",
        "data": {
            "call_id": "list-test-call",
            "from_number": "+15550001111",
        }
    })
    resp = await client.get("/api/v1/calls/")
    assert resp.status_code == 200
    calls = resp.json()
    assert len(calls) == 1
    assert calls[0]["call_id"] == "list-test-call"


@pytest.mark.asyncio
async def test_get_call_by_id(client):
    await client.post("/api/v1/webhooks/retell", json={
        "event": "call_ended",
        "data": {
            "call_id": "detail-test-call",
            "from_number": "+15550002222",
        }
    })
    resp = await client.get("/api/v1/calls/detail-test-call")
    assert resp.status_code == 200
    assert resp.json()["call_id"] == "detail-test-call"
