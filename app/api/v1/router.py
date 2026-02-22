from fastapi import APIRouter
from app.api.v1.endpoints import webhooks, calls, businesses, dashboard, onboarding, knowledge, ingest

api_router = APIRouter()
api_router.include_router(webhooks.router, prefix="/webhooks", tags=["webhooks"])
api_router.include_router(calls.router, prefix="/calls", tags=["calls"])
api_router.include_router(businesses.router, prefix="/businesses", tags=["businesses"])
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"])
api_router.include_router(onboarding.router, prefix="/onboarding", tags=["onboarding"])
api_router.include_router(knowledge.router, prefix="/knowledge", tags=["knowledge"])
api_router.include_router(ingest.router, prefix="/ingest", tags=["ingest"])
