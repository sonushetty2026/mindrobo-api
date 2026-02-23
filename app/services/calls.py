"""Call processing service.

Handles the core logic for saving calls, extracting lead data,
looking up business config, and triggering notifications.
"""

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.call import Call
from app.models.business import Business
from app.models.user import User
from app.models.lead import Lead, LeadSource
from app.services.sms import send_caller_confirmation, send_owner_summary
from app.services.blob_storage import blob_service
from app.services.email_service import email_service
from app.core.trial_limits import check_trial_limit_calls

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
    agent_id = call_data.get("agent_id", "")
    
    # Check trial limits before creating call
    if agent_id:
        business = await lookup_business(db, agent_id)
        if business:
            # Get the business owner (user) to check trial status
            user_result = await db.execute(
                select(User).where(User.business_id == business.id)
            )
            user = user_result.scalars().first()
            
            if user:
                # Check trial limit (will raise HTTPException if exceeded)
                await check_trial_limit_calls(db, agent_id, user)
    
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
    
    # Wire up call recording upload to Azure Blob (Issue #63)
    recording_url = call_data.get("recording_url")
    if recording_url:
        try:
            blob_url = await blob_service.upload_recording_from_url(
                call_id=call.call_id,
                recording_url=recording_url
            )
            if blob_url:
                call.recording_url = blob_url
                logger.info("Recording uploaded to blob: %s", blob_url)
        except Exception as e:
            logger.error("Failed to upload recording for call %s: %s", call.call_id, e)
    
    db.add(call)
    await db.commit()
    await db.refresh(call)
    logger.info("Call saved: %s → %s", call.call_id, outcome)
    
    # Create Lead record if we have enough information
    if outcome == "lead_captured" and call_data.get("agent_id"):
        try:
            business = await lookup_business(db, call_data.get("agent_id"))
            if business and (lead.get("lead_name") or lead.get("service_type")):
                lead_record = Lead(
                    business_id=business.id,
                    caller_name=lead.get("lead_name") or "Unknown",
                    caller_phone=call_data.get("from_number", ""),
                    service_needed=lead.get("service_type"),
                    notes=lead.get("summary"),
                    source=LeadSource.CALL,
                )
                db.add(lead_record)
                await db.commit()
                await db.refresh(lead_record)
                logger.info("Lead created: %s for business %s", lead_record.id, business.id)
                
                # Send email notification to owner
                if business.owner_email:
                    try:
                        await email_service.send_lead_notification(
                            owner_email=business.owner_email,
                            business_name=business.name,
                            lead_name=lead.get("lead_name") or "Unknown",
                            lead_phone=call_data.get("from_number", ""),
                            service_needed=lead.get("service_type"),
                        )
                    except Exception as e:
                        logger.error("Failed to send lead email notification: %s", e)
                
                # Send SMS to owner
                if business.owner_phone:
                    try:
                        service_text = f" needs {lead.get('service_type')}" if lead.get('service_type') else ""
                        from app.services.sms import _send_sms
                        await _send_sms(
                            to=business.owner_phone,
                            body=f"New lead: {lead.get('lead_name') or 'Unknown'}{service_text}. Call: {call_data.get('from_number', '')}"
                        )
                    except Exception as e:
                        logger.error("Failed to send lead SMS notification: %s", e)
        except Exception as e:
            logger.error("Failed to create lead record: %s", e)
    
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
