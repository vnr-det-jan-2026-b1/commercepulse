"""
CommercePulse MVP — FastAPI Application Entry Point
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
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
        
    # Auto-create missing tables (like AIProductAnalysis) without Alembic
    try:
        from app.models.models import Base
        from sqlalchemy import text
        async with engine.connect() as conn:
            # Must run outside of a transaction block. On some systems execution_options is a coroutine.
            conn = await conn.execution_options(isolation_level="AUTOCOMMIT")
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            print("[INFO] Database tables ensured.")
    except Exception as exc:
        print(f"[WARNING] Could not auto-create tables: {exc}")
        
    # Initialize Redis caching (with InMemory fallback)
    from fastapi_cache import FastAPICache
    from fastapi_cache.backends.redis import RedisBackend
    from fastapi_cache.backends.inmemory import InMemoryBackend
    import redis.asyncio as aioredis
    
    try:
        import asyncio
        redis_client = aioredis.from_url(
            settings.REDIS_URL, 
            encoding="utf-8", 
            decode_responses=False,
            socket_connect_timeout=2.0
        )
        # Ping to verify connection, force timeout
        await asyncio.wait_for(redis_client.ping(), timeout=2.0)
        FastAPICache.init(RedisBackend(redis_client), prefix="fastapi-cache")
        print("[INFO] Redis cache initialized.")
    except Exception as exc:
        print(f"[WARNING] Redis unreachable, falling back to in-memory cache: {exc}")
        FastAPICache.init(InMemoryBackend(), prefix="fastapi-cache")
        
    # Start the WebSocket Redis Pub/Sub listener (optional/best-effort)
    import asyncio
    from app.routes.websockets import manager
    try:
        asyncio.create_task(manager.listen_to_redis())
    except Exception:
        print("[WARNING] Could not start Redis Pub/Sub listener.")
        
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

import time
import logging

logger = logging.getLogger("api_requests")

@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    duration = time.time() - start_time
    logger.info(f"[{request.method}] {request.url.path} - {response.status_code} ({duration:.2f}s)")
    return response

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS if hasattr(settings, "CORS_ORIGINS") else ["http://localhost:3000", "http://localhost:4000", "http://127.0.0.1:4000", "http://127.0.0.1:3000"],
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
        from app.services.tasks import ping
        res = ping.delay()
        pong = res.get(timeout=1.0)
        payload["celery"] = "ok" if pong == "pong" else "error"
    except Exception:
        payload["celery"] = "error"

    return payload