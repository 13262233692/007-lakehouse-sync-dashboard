import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.config import settings
from app.database import init_db
from app.api import api_router

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Lakehouse Sync Dashboard backend...")
    await init_db()
    logger.info("Application startup complete")
    yield
    logger.info("Application shutdown complete")


app = FastAPI(
    title="Lakehouse Sync Dashboard API",
    description="API for managing and monitoring data lakehouse metadata synchronization",
    version=__version__,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api")


@app.get("/api/health")
async def health_check():
    return {
        "status": "healthy",
        "version": __version__,
        "sync_interval_minutes": settings.SYNC_INTERVAL_MINUTES,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
