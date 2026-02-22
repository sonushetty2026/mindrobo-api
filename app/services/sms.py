"""Twilio SMS service for MindRobo.

Sends two messages on call completion:
1. Confirmation to caller ("We got your request, someone will call back")
2. Summary + urgency to business owner
"""

import logging
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException
from app.core.config import settings

logger = logging.getLogger(__name__)


def _get_twilio_client() -> Client:
    return Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)


async def send_caller_confirmation(caller_phone: str, business_name: str = "our team") -> bool:
    """Send a confirmation SMS to the caller after their call ends."""
    body = (
        f"Thanks for calling {business_name}! "
        f"We've received your request and someone will get back to you shortly. "
        f"- Powered by MindRobo"
    )
    return await _send_sms(caller_phone, body)


async def send_owner_summary(
    owner_phone: str,
    caller_phone: str,
    lead_name: str | None,
    service_type: str | None,
    urgency: str | None,
    summary: str | None,
) -> bool:
    """Send a call summary SMS to the business owner."""
    parts = ["📞 New lead from MindRobo:"]
    if lead_name:
        parts.append(f"Name: {lead_name}")
    parts.append(f"Phone: {caller_phone}")
    if service_type:
        parts.append(f"Service: {service_type}")
    if urgency:
        parts.append(f"Urgency: {urgency.upper()}")
    if summary:
        # Truncate summary to keep SMS under 1600 chars
        parts.append(f"Summary: {summary[:300]}")
    parts.append("Reply STOP to opt out.")

    body = "\n".join(parts)
    return await _send_sms(owner_phone, body)


async def send_approval_request(
    owner_phone: str,
    call_id: str,
    caller_phone: str,
    lead_name: str | None,
    service_type: str | None,
    urgency: str | None,
) -> bool:
    """Send a booking approval request to the business owner.
    
    Owner can reply with YES or NO to approve/reject the booking.
    """
    parts = ["📞 New booking request from MindRobo:"]
    if lead_name:
        parts.append(f"Name: {lead_name}")
    parts.append(f"Phone: {caller_phone}")
    if service_type:
        parts.append(f"Service: {service_type}")
    if urgency:
        parts.append(f"Urgency: {urgency.upper()}")
    parts.append("")
    parts.append(f"Reply YES to approve or NO to reject.")
    parts.append(f"Ref: {call_id[:8]}")  # Short reference for tracking

    body = "\n".join(parts)
    return await _send_sms(owner_phone, body)


async def _send_sms(to: str, body: str) -> bool:
    """Send an SMS via Twilio. Returns True on success."""
    if not all([settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN, settings.TWILIO_PHONE_NUMBER]):
        logger.warning("Twilio credentials not configured — skipping SMS to %s", to)
        return False

    try:
        client = _get_twilio_client()
        message = client.messages.create(
            body=body,
            from_=settings.TWILIO_PHONE_NUMBER,
            to=to,
        )
        logger.info("SMS sent to %s — SID: %s", to, message.sid)
        return True
    except TwilioRestException as e:
        logger.error("Twilio error sending SMS to %s: %s", to, e)
        return False
    except Exception as e:
        logger.error("Unexpected error sending SMS to %s: %s", to, e)
        return False
