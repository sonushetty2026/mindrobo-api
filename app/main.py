from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, RedirectResponse
from app.api.v1.router import api_router
from app.core.config import settings
from app.core.seed import seed_test_account
from contextlib import asynccontextmanager


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    # Startup: seed test account
    await seed_test_account()
    yield
    # Shutdown: cleanup if needed


app = FastAPI(
    title="MindRobo API",
    description="AI Receptionist for Home Services — Retell.ai + FastAPI + Azure",
    version="0.1.0",
    lifespan=lifespan,
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
    """Serve the marketing landing page."""
    return load_template("landing.html")


@app.get("/signup", response_class=HTMLResponse)
async def signup_page():
    """Serve the signup page."""
    return load_template("signup.html")


@app.get("/login", response_class=HTMLResponse)
async def login_page():
    """Serve the login page."""
    return load_template("login.html")


@app.get("/forgot-password", response_class=HTMLResponse)
async def forgot_password_page():
    """Serve the forgot password page."""
    return load_template("forgot-password.html")


@app.get("/reset-password", response_class=HTMLResponse)
async def reset_password_page():
    """Serve the password reset page with token."""
    return load_template("reset-password.html")


@app.get("/verify-email", response_class=HTMLResponse)
async def verify_email_page():
    """Serve the email verification page with token."""
    return load_template("verify-email.html")


@app.get("/logout")
async def logout():
    """Logout redirect - client will clear JWT and redirect."""
    return RedirectResponse(url="/login")


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
