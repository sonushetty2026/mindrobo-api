"""Retell.ai and Twilio webhook handlers.

On call_ended:
1. Parse Retell payload → extract lead data from call_analysis
2. Save Call record to PostgreSQL
3. Send confirmation SMS to caller
4. Send summary SMS to business owner
"""

from fastapi import APIRouter, Request, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.models.call import Call
from app.services.sms import send_caller_confirmation, send_owner_summary
import logging

router = APIRouter()
logger = logging.getLogger(__name__)


def _extract_lead_data(call_analysis: dict | None) -> dict:
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


@router.post("/retell")
async def retell_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    """Receive events from Retell.ai: call_started, call_ended, call_analyzed."""
    try:
        payload = await request.json()
        event = payload.get("event")
        call_data = payload.get("data", {})
        logger.info("Retell event received: %s | call_id=%s", event, call_data.get("call_id"))

        if event == "call_started":
            return {"status": "ok", "message": "call_started acknowledged"}

        elif event == "call_ended":
            call_id = call_data.get("call_id")
            if not call_id:
                raise HTTPException(status_code=400, detail="Missing call_id in payload")

            caller_phone = call_data.get("from_number", "")
            transcript = call_data.get("transcript", "")
            call_analysis = call_data.get("call_analysis")
            lead = _extract_lead_data(call_analysis)

            # Determine outcome
            outcome = "lead_captured" if lead.get("lead_name") or lead.get("service_type") else "callback_scheduled"

            # Save to DB
            call = Call(
                call_id=call_id,
                caller_phone=caller_phone,
                business_id=call_data.get("agent_id", ""),
                status="completed",
                outcome=outcome,
                transcript=transcript,
                summary=lead.get("summary"),
                lead_name=lead.get("lead_name"),
                lead_address=lead.get("lead_address"),
                service_type=lead.get("service_type"),
                urgency=lead.get("urgency"),
            )
            db.add(call)
            await db.commit()
            await db.refresh(call)
            logger.info("Call saved: %s → %s", call_id, outcome)

            # Send SMS notifications (fire-and-forget, don't fail the webhook)
            try:
                if caller_phone:
                    await send_caller_confirmation(caller_phone)
            except Exception as e:
                logger.error("SMS to caller failed: %s", e)

            # TODO: look up owner phone from business config table
            # For now, owner_phone must be passed via call metadata or env
            owner_phone = call_data.get("metadata", {}).get("owner_phone", "")
            if owner_phone:
                try:
                    await send_owner_summary(
                        owner_phone=owner_phone,
                        caller_phone=caller_phone,
                        lead_name=lead.get("lead_name"),
                        service_type=lead.get("service_type"),
                        urgency=lead.get("urgency"),
                        summary=lead.get("summary"),
                    )
                except Exception as e:
                    logger.error("SMS to owner failed: %s", e)

            return {"status": "ok", "call_id": call_id, "outcome": outcome}

        elif event == "call_analyzed":
            # Late analysis update — update existing call record
            call_id = call_data.get("call_id")
            if call_id:
                from sqlalchemy import select
                result = await db.execute(select(Call).where(Call.call_id == call_id))
                call = result.scalar_one_or_none()
                if call:
                    lead = _extract_lead_data(call_data.get("call_analysis"))
                    for field, value in lead.items():
                        if value:
                            setattr(call, field, value)
                    await db.commit()
                    logger.info("Call updated with analysis: %s", call_id)
            return {"status": "ok"}

        return {"status": "ok", "event": event}

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Webhook error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/twilio/sms")
async def twilio_sms_webhook(request: Request):
    """Receive inbound SMS replies from Twilio."""
    form = await request.form()
    from_number = form.get("From", "")
    body = form.get("Body", "")
    logger.info("Inbound SMS from %s: %s", from_number, body[:100])
    # TODO: route inbound SMS to business owner or CRM
    return {"status": "ok"}
