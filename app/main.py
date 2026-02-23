from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from app.api.v1.router import api_router
from app.core.config import settings

app = FastAPI(
    title="MindRobo API",
    description="AI Receptionist for Home Services — Retell.ai + FastAPI + Azure",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")

# Load templates
TEMPLATES_DIR = Path(__file__).parent / "templates"


def load_template(filename: str) -> str:
    """Load an HTML template from the templates directory."""
    template_path = TEMPLATES_DIR / filename
    if template_path.exists():
        return template_path.read_text()
    return f"<html><body><h1>Template not found: {filename}</h1></body></html>"


@app.get("/", response_class=HTMLResponse)
async def landing_page():
    """Serve the main landing page with dashboard links."""
    return load_template("index.html")


@app.get("/health")
async def health():
    return {"status": "ok", "service": "mindrobo-api", "version": "0.1.0"}


@app.get("/onboarding", response_class=HTMLResponse)
async def onboarding_page():
    """Serve the onboarding wizard page."""
    return load_template("onboarding.html")


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page():
    """Serve the live call dashboard page."""
    return load_template("dashboard.html")


@app.get("/analytics", response_class=HTMLResponse)
async def analytics_page():
    """Serve the analytics dashboard page."""
    return load_template("analytics.html")


@app.get("/warroom", response_class=HTMLResponse)
async def warroom_page():
    """Serve the war room agent monitor page."""
    return load_template("warroom.html")
