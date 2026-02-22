"""Tests for SMS service — verifies behavior when Twilio is not configured."""

import pytest
from app.services.sms import send_caller_confirmation, send_owner_summary


@pytest.mark.asyncio
async def test_sms_skipped_when_no_credentials():
    """SMS should gracefully return False when Twilio creds are empty."""
    result = await send_caller_confirmation("+15551234567")
    assert result is False


@pytest.mark.asyncio
async def test_owner_sms_skipped_when_no_credentials():
    result = await send_owner_summary(
        owner_phone="+15559999999",
        caller_phone="+15551234567",
        lead_name="Test Lead",
        service_type="plumbing",
        urgency="high",
        summary="Pipe burst in basement",
    )
    assert result is False
