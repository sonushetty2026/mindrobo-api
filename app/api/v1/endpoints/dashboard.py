"""WebSocket endpoint for live call dashboard.

Clients connect via ws://host/api/v1/dashboard/ws
and receive JSON messages when new calls come in.
"""

import asyncio
import json
import logging
from typing import Set

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.models.call import Call

router = APIRouter()
logger = logging.getLogger(__name__)

# In-memory set of connected clients (fine for single-process; use Redis pub/sub for multi-process)
_connections: Set[WebSocket] = set()


async def broadcast(message: dict):
    """Send a JSON message to all connected dashboard clients."""
    dead = set()
    for ws in _connections:
        try:
            await ws.send_json(message)
        except Exception:
            dead.add(ws)
    _connections.difference_update(dead)


@router.websocket("/ws")
async def dashboard_ws(websocket: WebSocket):
    """WebSocket connection for the call log dashboard."""
    await websocket.accept()
    _connections.add(websocket)
    logger.info("Dashboard client connected (%d total)", len(_connections))
    try:
        while True:
            # Keep connection alive; client can send pings
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        pass
    finally:
        _connections.discard(websocket)
        logger.info("Dashboard client disconnected (%d remaining)", len(_connections))


@router.get("/recent")
async def recent_calls(limit: int = 20, db: AsyncSession = Depends(get_db)):
    """HTTP fallback — get recent calls for initial dashboard load."""
    result = await db.execute(
        select(Call).order_by(Call.created_at.desc()).limit(limit)
    )
    calls = result.scalars().all()
    return [
        {
            "call_id": c.call_id,
            "caller_phone": c.caller_phone,
            "status": c.status,
            "outcome": c.outcome,
            "lead_name": c.lead_name,
            "service_type": c.service_type,
            "urgency": c.urgency,
            "summary": c.summary,
            "created_at": c.created_at.isoformat() if c.created_at else None,
        }
        for c in calls
    ]
