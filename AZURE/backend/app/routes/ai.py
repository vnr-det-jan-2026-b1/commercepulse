"""AI Brain routes — /ai/*"""
from datetime import date
from typing import Optional
import logging

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.core.security import rate_limiter, enforce_seller_scope
from app.services.embeddings import embedding_service
from app.services.tasks import auto_embed as auto_embed_task
from app.services.tasks import embed_single_product as embed_single_product_task

router = APIRouter(
    dependencies=[Depends(rate_limiter(max_requests=120, window_seconds=60))],
)
logger = logging.getLogger(__name__)


# ── Embed a single product snapshot ───────────────────────────
@router.post("/embed/product", summary="Embed one product's daily performance summary (async via Celery)")
async def embed_product(
    seller_id:  str,
    product_id: str,
    summary:    str,
    embed_date: Optional[str] = None,
    embed_type: str = "daily_snapshot",
    db:         AsyncSession = Depends(get_db),
    _scope:     str         = Depends(enforce_seller_scope),
):
    """
    Enqueue a Celery job to embed a single product summary.
    The HTTP request returns immediately with a task_id.
    """
    # We still accept a DB session for consistency / future auditing, but do not use it here.
    d_str = embed_date if embed_date else str(date.today())
    res = embed_single_product_task.delay(seller_id, product_id, summary, d_str, embed_type)
    logger.info(
        "[AI] Enqueued embed_single_product task_id=%s seller_id=%s product_id=%s date=%s",
        res.id,
        seller_id,
        product_id,
        d_str,
    )
    return {
        "status": "queued",
        "task_id": res.id,
        "product_id": product_id,
        "date": d_str,
    }


# ── Auto-embed (fast batch version) ───────────────────────────
@router.post("/embed/auto", summary="Auto-generate embeddings from latest ingested data (batch, async via Celery)")
async def auto_embed(
    seller_id:  str,
    snap_date:  Optional[str] = None,
    db:         AsyncSession = Depends(get_db),
    _scope:     str         = Depends(enforce_seller_scope),
):
    """
    Enqueue the batch auto-embed Celery job.
    Reuses the same logic as upload-triggered embedding.
    """
    # We accept snap_date in the same format the Celery task expects (YYYY-MM-DD).
    d_str = snap_date if snap_date else str(date.today())
    res = auto_embed_task.delay(seller_id, d_str)
    logger.info(
        "[AI] Enqueued auto_embed (manual) task_id=%s seller_id=%s date=%s",
        res.id,
        seller_id,
        d_str,
    )
    return {"status": "queued", "task_id": res.id, "seller_id": seller_id, "date": d_str}


# ── Similar products ──────────────────────────────────────────
@router.get("/similar-products", summary="Find similar products via pgvector cosine similarity")
async def similar_products(
    seller_id:  str,
    query:      str = Query(..., description="Natural language query, e.g. 'high ROAS electronics'"),
    limit:      int = Query(5, ge=1, le=20),
    embed_type: str = Query("daily_snapshot"),
    db:         AsyncSession = Depends(get_db),
    _scope:     str         = Depends(enforce_seller_scope),
):
    results = await embedding_service.find_similar_products(
        db, seller_id, query, limit=limit, embed_type=embed_type,
    )
    return {"seller_id": seller_id, "query": query, "results": results}


# ── Historical context retrieval ──────────────────────────────
@router.get("/historical-context", summary="Retrieve historical performance cases similar to a query")
async def historical_context(
    seller_id: str,
    query:     str = Query(...),
    limit:     int = Query(5, ge=1, le=20),
    db:        AsyncSession = Depends(get_db),
    _scope:    str         = Depends(enforce_seller_scope),
):
    results = await embedding_service.find_similar_products(db, seller_id, query, limit=limit)
    return {"seller_id": seller_id, "query": query,
            "context_count": len(results), "historical_context": results}


# ── Store an AI insight ───────────────────────────────────────
@router.post("/insights", summary="Store an AI-generated insight as an embedding")
async def store_insight(
    seller_id:    str,
    insight_text: str,
    insight_type: str = "general",
    insight_date: Optional[str] = None,
    db:           AsyncSession = Depends(get_db),
    _scope:       str         = Depends(enforce_seller_scope),
):
    d = date.fromisoformat(insight_date) if insight_date else date.today()
    await embedding_service.store_insight(db, seller_id, insight_text, insight_type, insight_date=d)
    return {"status": "ok", "insight_type": insight_type, "date": str(d)}


# ── Retrieve similar past insights ────────────────────────────
@router.get("/insights/similar", summary="Retrieve similar past AI insights")
async def similar_insights(
    seller_id: str,
    query:     str,
    limit:     int = Query(5, ge=1, le=20),
    db:        AsyncSession = Depends(get_db),
    _scope:    str         = Depends(enforce_seller_scope),
):
    results = await embedding_service.find_similar_insights(db, seller_id, query, limit=limit)
    return {"seller_id": seller_id, "query": query, "results": results}
