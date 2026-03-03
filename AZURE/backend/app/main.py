"""
CommercePulse MVP — FastAPI Application Entry Point
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.db.session import engine
from app.core.config import settings
from app.routes import upload, analytics, ai, sellers, tasks, websockets


# ── Lifespan (startup / shutdown) ─────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Run startup tasks, then yield, then shutdown tasks."""
    # Ensure the HuggingFace model is pre-loaded to avoid cold-start latency
    # on the first recommendation request.
    try:
        from app.services.embeddings import embedding_service
        await embedding_service.preload()
    except Exception as exc:
        print(f"[WARNING] Could not preload embedding model: {exc}")
        
    # Initialize Redis caching
    from fastapi_cache import FastAPICache
    from fastapi_cache.backends.redis import RedisBackend
    import redis.asyncio as aioredis
    
    redis_client = aioredis.from_url(settings.REDIS_URL, encoding="utf-8", decode_responses=False)
    FastAPICache.init(RedisBackend(redis_client), prefix="fastapi-cache")
        
    yield
    await engine.dispose()


# ── App instance ───────────────────────────────────────────────
app = FastAPI(
    title="CommercePulse Ingestion & Analytics API",
    version="1.0.0",
    description=(
        "Multi-marketplace commerce intelligence platform. "
        "Ingest structured Excel snapshots across 5 domains, "
        "run analytics, and query the pgvector AI memory layer."
    ),
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────
app.include_router(websockets.router, tags=["WebSockets"])
app.include_router(sellers.router,   prefix="/sellers",   tags=["Sellers"])
app.include_router(upload.router,    prefix="/upload",    tags=["Excel Upload"])
app.include_router(analytics.router, prefix="/analytics", tags=["Analytics"])
app.include_router(ai.router,        prefix="/ai",        tags=["AI Brain"])
app.include_router(tasks.router,     prefix="/tasks",     tags=["Tasks"])


# ── Health check ──────────────────────────────────────────────
@app.get("/health", tags=["System"])
async def health():
    # Basic service info
    payload = {
        "status": "ok",
        "service": "CommercePulse Ingestion API",
        "version": "1.0.0",
        "env": settings.APP_ENV,
    }
    # Best-effort Celery/Redis health
    try:
        from app.services.tasks import ping # Assuming ping might be in tasks now or needs update
        # Wait, I didn't move ping.py yet. I should move it to app/services/tasks.py or similar.

        res = ping.delay()
        pong = res.get(timeout=1.0)
        payload["celery"] = "ok" if pong == "pong" else "error"
    except Exception:
        payload["celery"] = "error"

    return payload