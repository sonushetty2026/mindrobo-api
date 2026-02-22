"""Call processing service.

Handles the core logic for saving calls, extracting lead data,
looking up business config, and triggering notifications.
"""

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.call import Call
from app.models.business import Business
from app.services.sms import send_caller_confirmation, send_owner_summary

logger = logging.getLogger(__name__)


def extract_lead_data(call_analysis: dict | None) -> dict:
    """Extract structured lead info from Retell's call_analysis JSON.

    Retell puts custom data in call_analysis.custom_analysis_data
    (dict of field_name → extracted_value). We map known fields.
    """
    if not call_analysis:
        return {}

    custom = call_analysis.get("custom_analysis_data", {})
    return {
        "lead_name": custom.get("caller_name") or custom.get("name"),
        "lead_address": custom.get("address") or custom.get("caller_address"),
        "service_type": custom.get("service_type") or custom.get("service_needed"),
        "urgency": custom.get("urgency") or custom.get("priority"),
        "summary": call_analysis.get("call_summary"),
    }


async def lookup_business(db: AsyncSession, agent_id: str) -> Business | None:
    """Find a business by its Retell agent ID."""
    if not agent_id:
        return None
    result = await db.execute(
        select(Business).where(Business.retell_agent_id == agent_id)
    )
    return result.scalar_one_or_none()


async def save_call(db: AsyncSession, call_data: dict, lead: dict) -> Call:
    """Create and persist a Call record. Returns the saved Call."""
    outcome = (
        "lead_captured"
        if lead.get("lead_name") or lead.get("service_type")
        else "callback_scheduled"
    )

    call = Call(
        call_id=call_data["call_id"],
        caller_phone=call_data.get("from_number", ""),
        business_id=call_data.get("agent_id", ""),
        status="completed",
        outcome=outcome,
        transcript=call_data.get("transcript", ""),
        summary=lead.get("summary"),
        lead_name=lead.get("lead_name"),
        lead_address=lead.get("lead_address"),
        service_type=lead.get("service_type"),
        urgency=lead.get("urgency"),
    )
    db.add(call)
    await db.commit()
    await db.refresh(call)
    logger.info("Call saved: %s → %s", call.call_id, outcome)
    return call


async def update_call_with_analysis(db: AsyncSession, call_id: str, call_analysis: dict | None) -> None:
    """Update an existing call record with late analysis data."""
    result = await db.execute(select(Call).where(Call.call_id == call_id))
    call = result.scalar_one_or_none()
    if not call:
        logger.warning("call_analyzed for unknown call_id: %s", call_id)
        return

    lead = extract_lead_data(call_analysis)
    for field, value in lead.items():
        if value:
            setattr(call, field, value)
    await db.commit()
    logger.info("Call updated with analysis: %s", call_id)


async def send_notifications(
    caller_phone: str,
    business: Business | None,
    lead: dict,
) -> None:
    """Send SMS notifications to caller and business owner.

    Failures are logged but never raised — SMS should not break the webhook.
    """
    business_name = business.name if business else "our team"

    if caller_phone:
        try:
            await send_caller_confirmation(caller_phone, business_name)
        except Exception as e:
            logger.error("SMS to caller %s failed: %s", caller_phone, e)

    if business and business.owner_phone:
        try:
            await send_owner_summary(
                owner_phone=business.owner_phone,
                caller_phone=caller_phone,
                lead_name=lead.get("lead_name"),
                service_type=lead.get("service_type"),
                urgency=lead.get("urgency"),
                summary=lead.get("summary"),
            )
        except Exception as e:
            logger.error("SMS to owner %s failed: %s", business.owner_phone, e)
