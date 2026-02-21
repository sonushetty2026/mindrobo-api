from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
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

@app.get("/health")
async def health():
    return {"status": "ok", "service": "mindrobo-api", "version": "0.1.0"}


@app.get("/dashboard")
async def dashboard_redirect():
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/api/v1/dashboard/")
