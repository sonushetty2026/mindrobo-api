"""WebSocket endpoint + HTML dashboard for live call logs.

- GET /api/v1/dashboard/ → Enhanced HTML dashboard with filters and business info
- GET /api/v1/dashboard/recent → JSON API for AJAX refresh
- WS  /api/v1/dashboard/ws → live push of new calls
"""

import asyncio
import logging
from typing import Set
from pathlib import Path

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, String
from app.core.database import get_db
from app.models.call import Call

router = APIRouter()
logger = logging.getLogger(__name__)

_connections: Set[WebSocket] = set()

# Load dashboard template
TEMPLATES_DIR = Path(__file__).parent.parent.parent.parent / "app" / "templates"
DASHBOARD_TEMPLATE_PATH = TEMPLATES_DIR / "dashboard.html"


def _load_dashboard_template() -> str:
    """Load the dashboard HTML template from file."""
    if not DASHBOARD_TEMPLATE_PATH.exists():
        logger.error("Dashboard template not found at %s", DASHBOARD_TEMPLATE_PATH)
        return "<html><body><h1>Dashboard template not found</h1></body></html>"
    return DASHBOARD_TEMPLATE_PATH.read_text()


async def broadcast(message: dict):
    """Send a JSON message to all connected dashboard clients."""
    dead = set()
    for ws in _connections:
        try:
            await ws.send_json(message)
        except Exception:
            dead.add(ws)
    _connections.difference_update(dead)


@router.get("/", response_class=HTMLResponse)
async def dashboard_page():
    """Serve the enhanced HTML call dashboard with business info and filters."""
    return _load_dashboard_template()


@router.websocket("/ws")
async def dashboard_ws(websocket: WebSocket):
    await websocket.accept()
    _connections.add(websocket)
    logger.info("Dashboard client connected (%d total)", len(_connections))
    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        pass
    finally:
        _connections.discard(websocket)
        logger.info("Dashboard client disconnected (%d remaining)", len(_connections))


@router.get("/recent")
async def recent_calls(limit: int = 50, db: AsyncSession = Depends(get_db)):
    """JSON endpoint for initial dashboard load with business info."""
    from app.models.business import Business
    from sqlalchemy import join
    
    # Join calls with businesses to get owner info
    result = await db.execute(
        select(Call, Business)
        .join(Business, Call.business_id == Business.id.cast(String), isouter=True)
        .order_by(Call.created_at.desc())
        .limit(limit)
    )
    rows = result.all()
    
    return [
        {
            "call_id": call.call_id,
            "caller_phone": call.caller_phone,
            "status": call.status,
            "outcome": call.outcome,
            "lead_name": call.lead_name,
            "lead_address": call.lead_address,
            "service_type": call.service_type,
            "urgency": call.urgency,
            "summary": call.summary,
            "transcript": call.transcript,
            "created_at": call.created_at.isoformat() if call.created_at else None,
            "business_name": business.name if business else "Unknown",
            "business_id": call.business_id,
            "owner_phone": business.owner_phone if business else None,
            "owner_name": business.owner_name if business else None,
        }
        for call, business in rows
    ]
