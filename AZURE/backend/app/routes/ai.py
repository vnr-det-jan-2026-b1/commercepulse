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

from app.services.ai_agent_client import trigger_simulation
from pydantic import BaseModel

class SimulateRequest(BaseModel):
    seller_id: str
    time_window_start: str
    time_window_end: str
    snapshot_data: dict

@router.post("/simulate", summary="Trigger the AI multi-agent simulation")
async def run_ai_simulation(
    request: SimulateRequest,
    db: AsyncSession = Depends(get_db),
    _scope: str = Depends(enforce_seller_scope),
):
    """
    Triggers the external LangGraph AI Agents API.
    """
    result = await trigger_simulation(
        seller_id=request.seller_id,
        time_window_start=request.time_window_start,
        time_window_end=request.time_window_end,
        snapshot_data=request.snapshot_data
    )
    if result and result.get("status") == "success":
        # Store the high-level plan in the database
        executive_plan = result.get("executive_plan", {})
        import json
        plan_text = json.dumps(executive_plan)
        # Create an embedding for the AI's action plan for future context retrieval
        await embedding_service.store_insight(
            db=db,
            seller_id=request.seller_id,
            insight_text=plan_text,
            insight_type="executive_action_plan",
            metadata={"source": "multi_agent_simulation"}
        )
        return result
    return {"status": "error", "message": "Failed to retrieve executive plan from AI agents."}

from fastapi.responses import StreamingResponse
from app.services.ai_agent_client import trigger_simulation_stream

@router.post("/simulate/stream", summary="Stream the AI multi-agent simulation response")
async def run_ai_simulation_stream(
    request: SimulateRequest,
    db: AsyncSession = Depends(get_db),
    _scope: str = Depends(enforce_seller_scope),
):
    """
    Triggers the LangGraph AI Agents API and streams the Synthesizer's response back to the client via SSE.
    """
    return StreamingResponse(
        trigger_simulation_stream(
            seller_id=request.seller_id,
            time_window_start=request.time_window_start,
            time_window_end=request.time_window_end,
            snapshot_data=request.snapshot_data
        ),
        media_type="text/event-stream"
    )

from app.services.ai_agent_client import trigger_whatif_stream

class WhatIfRequest(BaseModel):
    seller_id: str
    scenario: str

@router.post("/whatif", summary="Stream a hypothetical What-If scenario through the AI Agents")
async def run_whatif_simulation_stream(
    request: WhatIfRequest,
    db: AsyncSession = Depends(get_db),
    _scope: str = Depends(enforce_seller_scope),
):
    """
    Triggers the LangGraph AI Agents' What-If engine and streams the Synthesizer's response back via SSE.
    """
    return StreamingResponse(
        trigger_whatif_stream(
            seller_id=request.seller_id,
            scenario=request.scenario
        ),
        media_type="text/event-stream"
    )
