"""
CommercePulse++ FastAPI Backend
Cloud Run service — API layer for the analytics platform.
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.routes import analytics, intelligence, ai, upload, events

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("CommercePulse++ API starting up | project=%s", settings.GCP_PROJECT)
    yield
    logger.info("CommercePulse++ API shutting down")


app = FastAPI(
    title="CommercePulse++ API",
    version=settings.API_VERSION,
    description="Analytics and intelligence platform for e-commerce sellers — Google Cloud Edition",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(events.router)
app.include_router(analytics.router,    prefix="/v1")
app.include_router(intelligence.router, prefix="/v1")
app.include_router(ai.router,           prefix="/v1")
app.include_router(upload.router,       prefix="/v1")


@app.get("/health", tags=["system"])
async def health():
    return {
        "status":  "ok",
        "version": settings.API_VERSION,
        "project": settings.GCP_PROJECT,
    }


@app.get("/", include_in_schema=False)
async def root():
    return {"message": "CommercePulse++ API", "docs": "/docs"}
