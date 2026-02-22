from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, RedirectResponse
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

# Load landing page template
TEMPLATES_DIR = Path(__file__).parent / "templates"
LANDING_PAGE_PATH = TEMPLATES_DIR / "index.html"


@app.get("/", response_class=HTMLResponse)
async def landing_page():
    """Serve the main landing page with dashboard links."""
    if LANDING_PAGE_PATH.exists():
        return LANDING_PAGE_PATH.read_text()
    return "<html><body><h1>MindRobo API</h1><p>Landing page not found</p></body></html>"


@app.get("/health")
async def health():
    return {"status": "ok", "service": "mindrobo-api", "version": "0.1.0"}


@app.get("/dashboard")
async def dashboard_redirect():
    return RedirectResponse(url="/api/v1/dashboard/")


@app.get("/onboarding")
async def onboarding_redirect():
    return RedirectResponse(url="/api/v1/onboarding/")


@app.get("/analytics")
async def analytics_redirect():
    return RedirectResponse(url="/api/v1/analytics/")


@app.get("/warroom")
async def warroom_redirect():
    return RedirectResponse(url="/api/v1/warroom/")
