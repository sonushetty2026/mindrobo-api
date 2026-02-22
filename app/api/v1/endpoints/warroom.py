"""War Room dashboard - real-time agent status monitoring.

- GET /api/v1/warroom/ → HTML war room dashboard
- GET /api/v1/warroom/status → JSON status of all agents
"""

import logging
from pathlib import Path
from datetime import datetime

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter()
logger = logging.getLogger(__name__)

# Load war room template
TEMPLATES_DIR = Path(__file__).parent.parent.parent.parent / "app" / "templates"
WARROOM_TEMPLATE_PATH = TEMPLATES_DIR / "warroom.html"


def _load_warroom_template() -> str:
    """Load the war room HTML template from file."""
    if not WARROOM_TEMPLATE_PATH.exists():
        logger.error("War room template not found at %s", WARROOM_TEMPLATE_PATH)
        return "<html><body><h1>War room template not found</h1></body></html>"
    return WARROOM_TEMPLATE_PATH.read_text()


@router.get("/", response_class=HTMLResponse)
async def warroom_page():
    """Serve the war room dashboard HTML."""
    return _load_warroom_template()


@router.get("/status")
async def get_agent_status():
    """Get current status of all agents.
    
    In production, this would poll OpenClaw sessions API.
    For now, returns mock data structure.
    """
    # TODO: Integrate with OpenClaw sessions API
    # For now, return a mock structure showing what agents would report
    
    agents = [
        {
            "id": "orchestrator",
            "name": "Orchestrator",
            "role": "Task coordination & routing",
            "status": "active",  # active, idle, thinking, offline
            "last_action": "Assigned Issue #29 to Frontend",
            "last_update": datetime.utcnow().isoformat(),
            "color": "blue",
        },
        {
            "id": "backend",
            "name": "Backend",
            "role": "API development & database",
            "status": "active",
            "last_action": "Working on Issue #36 - Analytics API",
            "last_update": datetime.utcnow().isoformat(),
            "color": "purple",
        },
        {
            "id": "frontend",
            "name": "Frontend",
            "role": "UI/UX & dashboards",
            "status": "active",
            "last_action": "Building War Room dashboard (Issue #29)",
            "last_update": datetime.utcnow().isoformat(),
            "color": "cyan",
        },
        {
            "id": "qa",
            "name": "QA",
            "role": "Testing & quality assurance",
            "status": "idle",
            "last_action": "Reviewing PR #48",
            "last_update": datetime.utcnow().isoformat(),
            "color": "green",
        },
        {
            "id": "ingestion",
            "name": "Ingestion",
            "role": "Data processing & ML pipelines",
            "status": "idle",
            "last_action": "Completed Issue #20 - Voice tuning",
            "last_update": datetime.utcnow().isoformat(),
            "color": "orange",
        },
    ]
    
    return {
        "agents": agents,
        "system_status": "operational",
        "active_agents": sum(1 for a in agents if a["status"] == "active"),
        "total_agents": len(agents),
        "last_refresh": datetime.utcnow().isoformat(),
    }
