from fastapi import APIRouter

from app.api.assets import router as assets_router
from app.api.stats import router as stats_router
from app.api.sync import router as sync_router

api_router = APIRouter()

api_router.include_router(assets_router)
api_router.include_router(stats_router)
api_router.include_router(sync_router)
