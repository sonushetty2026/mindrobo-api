from fastapi import APIRouter
from app.api.v1.endpoints import (
    auth,
    billing,
    webhooks,
    calls,
    businesses,
    dashboard,
    onboarding,
    knowledge,
    ingest,
    analytics,
    warroom,
    appointments,
    leads,
)

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(billing.router, prefix="/billing", tags=["billing"])
api_router.include_router(webhooks.router, prefix="/webhooks", tags=["webhooks"])
api_router.include_router(calls.router, prefix="/calls", tags=["calls"])
api_router.include_router(businesses.router, prefix="/businesses", tags=["businesses"])
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"])
api_router.include_router(onboarding.router, prefix="/onboarding", tags=["onboarding"])
api_router.include_router(knowledge.router, prefix="/knowledge", tags=["knowledge"])
api_router.include_router(ingest.router, prefix="/ingest", tags=["ingest"])
api_router.include_router(analytics.router, prefix="/analytics", tags=["analytics"])
api_router.include_router(warroom.router, prefix="/warroom", tags=["warroom"])
api_router.include_router(appointments.router, prefix="/api", tags=["appointments"])
api_router.include_router(leads.router, prefix="/leads", tags=["leads"])
