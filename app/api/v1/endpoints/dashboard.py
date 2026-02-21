"""WebSocket endpoint + HTML dashboard for live call logs.

- GET /api/v1/dashboard/ → HTML page showing last 20 calls
- GET /api/v1/dashboard/recent → JSON API for AJAX refresh
- WS  /api/v1/dashboard/ws → live push of new calls
"""

import asyncio
import logging
from typing import Set

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.models.call import Call

router = APIRouter()
logger = logging.getLogger(__name__)

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


DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>MindRobo — Call Dashboard</title>
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #0f172a; color: #e2e8f0; padding: 24px; }
  h1 { font-size: 1.5rem; margin-bottom: 16px; color: #38bdf8; }
  .badge { display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 0.75rem; font-weight: 600; text-transform: uppercase; }
  .badge-high { background: #dc2626; color: #fff; }
  .badge-medium { background: #f59e0b; color: #000; }
  .badge-low { background: #22c55e; color: #000; }
  .badge-lead { background: #6366f1; color: #fff; }
  .badge-callback { background: #64748b; color: #fff; }
  table { width: 100%; border-collapse: collapse; }
  th { text-align: left; padding: 10px 12px; background: #1e293b; color: #94a3b8; font-size: 0.8rem; text-transform: uppercase; letter-spacing: 0.05em; }
  td { padding: 10px 12px; border-bottom: 1px solid #1e293b; font-size: 0.9rem; }
  tr:hover td { background: #1e293b; }
  .empty { text-align: center; padding: 40px; color: #64748b; }
  .live-dot { display: inline-block; width: 8px; height: 8px; background: #22c55e; border-radius: 50%; margin-right: 8px; animation: pulse 2s infinite; }
  @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.4; } }
  .header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 16px; }
  .status { font-size: 0.8rem; color: #64748b; }
</style>
</head>
<body>
<div class="header">
  <h1>📞 MindRobo Call Dashboard</h1>
  <div class="status"><span class="live-dot"></span><span id="ws-status">Connecting...</span></div>
</div>
<table>
  <thead>
    <tr>
      <th>Time</th>
      <th>Caller</th>
      <th>Lead Name</th>
      <th>Service</th>
      <th>Urgency</th>
      <th>Outcome</th>
    </tr>
  </thead>
  <tbody id="calls"></tbody>
</table>
<script>
function urgencyBadge(u) {
  if (!u) return '-';
  const cls = u.toLowerCase() === 'high' ? 'badge-high' : u.toLowerCase() === 'medium' ? 'badge-medium' : 'badge-low';
  return `<span class="badge ${cls}">${u}</span>`;
}
function outcomeBadge(o) {
  if (!o) return '-';
  const cls = o === 'lead_captured' ? 'badge-lead' : 'badge-callback';
  return `<span class="badge ${cls}">${o.replace('_', ' ')}</span>`;
}
function formatTime(iso) {
  if (!iso) return '-';
  const d = new Date(iso);
  return d.toLocaleString();
}
function renderRow(c) {
  return `<tr>
    <td>${formatTime(c.created_at)}</td>
    <td>${c.caller_phone || '-'}</td>
    <td>${c.lead_name || '-'}</td>
    <td>${c.service_type || '-'}</td>
    <td>${urgencyBadge(c.urgency)}</td>
    <td>${outcomeBadge(c.outcome)}</td>
  </tr>`;
}
const tbody = document.getElementById('calls');
const wsStatus = document.getElementById('ws-status');

// Initial load
fetch('/api/v1/dashboard/recent?limit=20')
  .then(r => r.json())
  .then(calls => {
    if (calls.length === 0) {
      tbody.innerHTML = '<tr><td colspan="6" class="empty">No calls yet</td></tr>';
    } else {
      tbody.innerHTML = calls.map(renderRow).join('');
    }
  });

// WebSocket for live updates
function connectWS() {
  const proto = location.protocol === 'https:' ? 'wss:' : 'ws:';
  const ws = new WebSocket(`${proto}//${location.host}/api/v1/dashboard/ws`);
  ws.onopen = () => { wsStatus.textContent = 'Live'; };
  ws.onclose = () => { wsStatus.textContent = 'Reconnecting...'; setTimeout(connectWS, 3000); };
  ws.onmessage = (e) => {
    const msg = JSON.parse(e.data);
    if (msg.event === 'new_call') {
      const empty = tbody.querySelector('.empty');
      if (empty) empty.parentElement.remove();
      tbody.insertAdjacentHTML('afterbegin', renderRow(msg));
      // Keep max 20 rows
      while (tbody.children.length > 20) tbody.removeChild(tbody.lastChild);
    }
  };
}
connectWS();
</script>
</body>
</html>"""


@router.get("/", response_class=HTMLResponse)
async def dashboard_page():
    """Serve the HTML call dashboard."""
    return DASHBOARD_HTML


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
async def recent_calls(limit: int = 20, db: AsyncSession = Depends(get_db)):
    """JSON endpoint for initial dashboard load."""
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
