"""Tests for business CRUD endpoints."""

import pytest


@pytest.mark.asyncio
async def test_create_and_list_business(client):
    """Create a business and verify it appears in the list."""
    resp = await client.post("/api/v1/businesses/", json={
        "name": "Acme Roofing",
        "owner_phone": "+15551112222",
        "owner_name": "Bob",
        "retell_agent_id": "agent-acme",
    })
    assert resp.status_code == 201
    biz = resp.json()
    assert biz["name"] == "Acme Roofing"
    assert biz["owner_phone"] == "+15551112222"
    assert biz["is_active"] is True

    # Should appear in list
    resp2 = await client.get("/api/v1/businesses/")
    assert resp2.status_code == 200
    assert len(resp2.json()) == 1


@pytest.mark.asyncio
async def test_get_business_not_found(client):
    resp = await client.get("/api/v1/businesses/00000000-0000-0000-0000-000000000000")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_webhook_looks_up_owner_phone(client):
    """When a business exists with matching retell_agent_id, webhook should find owner_phone."""
    from unittest.mock import patch, AsyncMock

    # Create business first
    await client.post("/api/v1/businesses/", json={
        "name": "Storm Roofing",
        "owner_phone": "+15553334444",
        "retell_agent_id": "agent-storm",
    })

    with patch("app.services.calls.send_caller_confirmation", new_callable=AsyncMock) as mock_caller, \
         patch("app.services.calls.send_owner_summary", new_callable=AsyncMock) as mock_owner, \
         patch("app.api.v1.endpoints.webhooks.broadcast", new_callable=AsyncMock):

        await client.post("/api/v1/webhooks/retell", json={
            "event": "call_ended",
            "data": {
                "call_id": "owner-lookup-test",
                "from_number": "+15559998888",
                "agent_id": "agent-storm",
                "call_analysis": {
                    "call_summary": "Needs gutter repair",
                    "custom_analysis_data": {"caller_name": "Jane"}
                }
            }
        })

        mock_caller.assert_called_once()
        mock_owner.assert_called_once()
        # Verify owner_phone was resolved from business table
        assert mock_owner.call_args.kwargs.get("owner_phone") == "+15553334444" or \
               mock_owner.call_args[1].get("owner_phone") == "+15553334444" or \
               "+15553334444" in str(mock_owner.call_args)
