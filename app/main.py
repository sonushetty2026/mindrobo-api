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


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page():
    template = TEMPLATES_DIR / "dashboard.html"
    if template.exists():
        return HTMLResponse(content=template.read_text())
    return HTMLResponse(content="<h1>Dashboard template not found</h1>", status_code=500)


@app.get("/onboarding", response_class=HTMLResponse)
async def onboarding_page():
    template = TEMPLATES_DIR / "onboarding.html"
    if template.exists():
        return HTMLResponse(content=template.read_text())
    return HTMLResponse(content="<h1>Onboarding template not found</h1>", status_code=500)


@app.get("/analytics", response_class=HTMLResponse)
async def analytics_page():
    template = TEMPLATES_DIR / "analytics.html"
    if template.exists():
        return HTMLResponse(content=template.read_text())
    return HTMLResponse(content="<h1>Analytics template not found</h1>", status_code=500)


@app.get("/warroom", response_class=HTMLResponse)
async def warroom_page():
    template = TEMPLATES_DIR / "warroom.html"
    if template.exists():
        return HTMLResponse(content=template.read_text())
    return HTMLResponse(content="<h1>War Room template not found</h1>", status_code=500)


@app.get("/leads", response_class=HTMLResponse)
async def leads_page():
    return load_template("leads.html")


@app.get("/billing", response_class=HTMLResponse)
async def billing_page():
    return load_template("billing.html")


@app.get("/settings", response_class=HTMLResponse)
async def settings_page():
    return load_template("settings.html")


@app.get("/appointments", response_class=HTMLResponse)
async def appointments_page():
    return load_template("appointments.html")


@app.get("/phone-setup", response_class=HTMLResponse)
async def phone_setup_page():
    return load_template("phone-setup.html")


@app.get("/admin", response_class=HTMLResponse)
async def admin_dashboard_page():
    """Serve the admin dashboard page."""
    return load_template("admin_dashboard.html")


@app.get("/admin/users", response_class=HTMLResponse)
async def admin_users_page():
    """Serve the admin user management page."""
    return load_template("admin_users.html")


@app.get("/admin/trials", response_class=HTMLResponse)
async def admin_trials_page():
    """Serve the admin trial monitor page."""
    return load_template("admin_trials.html")


@app.get("/admin/usage", response_class=HTMLResponse)
async def admin_usage_page():
    """Serve the admin usage dashboard page."""
    return load_template("admin_usage.html")


@app.get("/admin/audit", response_class=HTMLResponse)
async def admin_audit_page():
    """Serve the admin audit log page."""
    return load_template("admin_audit.html")


@app.get("/admin/health-check", response_class=HTMLResponse)
async def admin_health_page():
    """Serve the admin integration health check page."""
    return load_template("admin_health.html")


@app.get("/admin/email-templates", response_class=HTMLResponse)
async def admin_email_templates_page():
    """Serve the admin email templates customization page."""
    return load_template("admin_email_templates.html")


@app.get("/account/sessions", response_class=HTMLResponse)
async def account_sessions_page():
    """Serve the user session management page."""
    return load_template("account_sessions.html")


@app.get("/notifications", response_class=HTMLResponse)
async def notifications_page():
    """Serve the notifications center page."""
    return load_template("admin_notifications.html")
