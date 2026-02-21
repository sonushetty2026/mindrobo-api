from fastapi import APIRouter, Request, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/retell")
async def retell_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    """Receive events from Retell.ai: call_started, call_ended, transcript"""
    try:
        payload = await request.json()
        event = payload.get("event")
        logger.info(f"Retell event received: {event}")

        if event == "call_started":
            return {"status": "ok", "message": "call_started acknowledged"}

        elif event == "call_ended":
            # TODO: save transcript, trigger SMS notification, create lead ticket
            return {"status": "ok", "message": "call_ended acknowledged"}

        elif event == "transcript":
            # TODO: stream transcript chunks to dashboard via WebSocket
            return {"status": "ok"}

        return {"status": "ok", "event": event}
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/twilio/sms")
async def twilio_sms_webhook(request: Request):
    """Receive inbound SMS replies from Twilio"""
    return {"status": "ok"}
