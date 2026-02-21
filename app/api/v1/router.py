from fastapi import APIRouter
from app.api.v1.endpoints import webhooks, calls

api_router = APIRouter()
api_router.include_router(webhooks.router, prefix="/webhooks", tags=["webhooks"])
api_router.include_router(calls.router, prefix="/calls", tags=["calls"])
