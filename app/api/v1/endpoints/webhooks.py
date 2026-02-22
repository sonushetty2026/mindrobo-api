"""Retell.ai and Twilio webhook handlers.

Thin HTTP layer — all business logic lives in app.services.calls.
"""

import logging

from fastapi import APIRouter, Request, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.calls import (
    extract_lead_data,
    lookup_business,
    save_call,
    update_call_with_analysis,
    send_notifications,
)
from app.api.v1.endpoints.dashboard import broadcast

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/retell")
async def retell_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    """Receive events from Retell.ai: call_started, call_ended, call_analyzed."""
    try:
        payload = await request.json()
        event = payload.get("event")
        call_data = payload.get("data", {})
        logger.info("Retell event: %s | call_id=%s", event, call_data.get("call_id"))

        if event == "call_started":
            return {"status": "ok", "message": "call_started acknowledged"}

        if event == "call_ended":
            return await _handle_call_ended(call_data, db)

        if event == "call_analyzed":
            call_id = call_data.get("call_id")
            if call_id:
                await update_call_with_analysis(db, call_id, call_data.get("call_analysis"))
            return {"status": "ok"}

        return {"status": "ok", "event": event}

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Webhook error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


async def _handle_call_ended(call_data: dict, db: AsyncSession) -> dict:
    """Process a call_ended event: save → notify → broadcast."""
    call_id = call_data.get("call_id")
    if not call_id:
        raise HTTPException(status_code=400, detail="Missing call_id in payload")

    lead = extract_lead_data(call_data.get("call_analysis"))
    call = await save_call(db, call_data, lead)
    business = await lookup_business(db, call_data.get("agent_id", ""))

    await send_notifications(
        caller_phone=call_data.get("from_number", ""),
        business=business,
        lead=lead,
    )

    try:
        await broadcast({
            "event": "new_call",
            "call_id": call.call_id,
            "caller_phone": call.caller_phone,
            "status": call.status,
            "outcome": call.outcome,
            "lead_name": call.lead_name,
            "service_type": call.service_type,
            "urgency": call.urgency,
            "summary": call.summary,
            "created_at": call.created_at.isoformat() if call.created_at else None,
        })
    except Exception as e:
        logger.error("WebSocket broadcast failed: %s", e)

    return {"status": "ok", "call_id": call_id, "outcome": call.outcome}


@router.post("/twilio/sms")
async def twilio_sms_webhook(request: Request):
    """Receive inbound SMS replies from Twilio."""
    form = await request.form()
    from_number = form.get("From", "")
    body = form.get("Body", "")
    logger.info("Inbound SMS from %s: %s", from_number, body[:100])
    return {"status": "ok"}
