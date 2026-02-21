"""Tests for business CRUD endpoints."""

import pytest


@pytest.mark.asyncio
async def test_create_business(client):
    resp = await client.post("/api/v1/businesses/", json={
        "name": "Acme Roofing",
        "owner_phone": "+15551112222",
        "owner_name": "Jane Smith",
        "retell_agent_id": "agent-acme",
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Acme Roofing"
    assert data["owner_phone"] == "+15551112222"
    assert data["is_active"] is True


@pytest.mark.asyncio
async def test_list_businesses(client):
    await client.post("/api/v1/businesses/", json={
        "name": "Acme Roofing",
        "owner_phone": "+15551112222",
    })
    resp = await client.get("/api/v1/businesses/")
    assert resp.status_code == 200
    assert len(resp.json()) == 1


@pytest.mark.asyncio
async def test_list_businesses_empty(client):
    resp = await client.get("/api/v1/businesses/")
    assert resp.status_code == 200
    assert resp.json() == []
