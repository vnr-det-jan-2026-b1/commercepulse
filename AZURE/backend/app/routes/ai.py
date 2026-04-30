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

# ── AI Business Analyst Chat ──────────────────────────────────
from pydantic import BaseModel
from fastapi import HTTPException
import httpx
from app.core.config import settings

class ChatRequest(BaseModel):
    message: str
    history: list = []
    context: dict = {}

@router.post("/chat", summary="Chat with the AI Business Analyst")
async def ai_chat(
    request: ChatRequest,
    seller_id: str = Query(...),
    db: AsyncSession = Depends(get_db),
    _scope: str = Depends(enforce_seller_scope),
):
    groq_api_key = settings.GROQ_API_KEY.strip().strip('"').strip("'")
    logger.info(f"[AI Chat] Using Groq key: {groq_api_key[:8]}...{groq_api_key[-4:]} (len={len(groq_api_key)})")
    if not groq_api_key:
        raise HTTPException(status_code=500, detail="GROQ_API_KEY is missing from environment")
    
    ctx = request.context
    context_str = f"""
- Revenue (Last {ctx.get('period_days', 30)} days): ₹{ctx.get('total_revenue', 0):,}
- Total Orders: {ctx.get('total_orders', 0)}
- Return Rate: {ctx.get('return_rate_pct', 0)}%
- Avg Margin: {ctx.get('avg_margin_pct', 0)}%
- Avg ROAS: {ctx.get('avg_roas', 0)}
"""
    
    system_prompt = f"""You are a Senior Business Analyst for a D2C coffee brand named "Brew Boulevard". 
Your job is to answer the user's questions strictly based on their real data.
Be concise, highly professional, use bullet points if needed, and reference actual Rs amounts, percentages, and units.

Here is the LIVE DATA context for Brew Boulevard:
{context_str}

Rules:
1. Do not hallucinate metrics. If the data isn't in the context, say you don't have that specific data point.
2. Be aggressive about growth and protecting margins.
3. Keep responses under 150 words unless explaining a complex strategy.
4. If asked about revenue, immediately reference the actual amount.
5. Provide actionable advice for D2C scaling."""

    messages = [{"role": "system", "content": system_prompt}]
    
    for msg in request.history:
        messages.append({
            "role": "assistant" if msg.get("type") == "ai" else "user",
            "content": msg.get("text", "")
        })
        
    messages.append({"role": "user", "content": request.message})

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {groq_api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "llama-3.1-8b-instant",
                    "messages": messages,
                    "temperature": 0.3,
                    "max_tokens": 500,
                },
                timeout=30.0
            )
            response.raise_for_status()
            data = response.json()
            return {"reply": data["choices"][0]["message"]["content"]}
        except Exception as e:
            logger.error(f"Groq API Error: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))


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

from app.services.ai_agent_client import trigger_product_analysis
from app.models.models import AIProductAnalysis
from sqlalchemy import select, text

@router.post("/analyze/product", summary="Trigger AI analysis for a specific product")
async def analyze_product(
    seller_id: str,
    product_id: str,
    db: AsyncSession = Depends(get_db),
    _scope: str = Depends(enforce_seller_scope),
):
    """
    Triggers the per-product multi-agent analysis and stores the result.
    """
    # ── 1. Core product info + aggregated KPIs ──
    metrics_sql = text("""
        WITH revenue_stats AS (
            SELECT product_id,
                   SUM(selling_price * quantity) AS total_revenue,
                   COUNT(*) AS total_orders,
                   ROUND(AVG(selling_price * quantity), 2) AS avg_order_value,
                   SUM(CASE WHEN discount > 0 THEN 1 ELSE 0 END) AS discounted_orders,
                   SUM(discount) AS total_discount_given,
                   SUM(shipping_fee) AS total_shipping_collected,
                   SUM(tax) AS total_tax_collected
            FROM orders
            WHERE seller_id = CAST(:seller_id AS UUID) AND product_id = CAST(:product_id AS UUID)
            GROUP BY product_id
        ),
        return_stats AS (
            SELECT product_id,
                   COUNT(*) FILTER (WHERE return_flag = true) AS total_returns,
                   COUNT(*) AS total_fulfilled,
                   ROUND(COUNT(*) FILTER (WHERE return_flag = true) * 100.0 / NULLIF(COUNT(*), 0), 1) AS return_rate_pct
            FROM orders
            WHERE seller_id = CAST(:seller_id AS UUID) AND product_id = CAST(:product_id AS UUID)
              AND order_status IN ('delivered', 'returned')
            GROUP BY product_id
        ),
        stock_stats AS (
            SELECT product_id,
                   SUM(available_stock) AS stock_level,
                   SUM(reserved_stock) AS reserved_stock,
                   MAX(reorder_threshold) AS reorder_threshold,
                   MAX(days_of_stock) AS days_of_stock
            FROM inventory_snapshots
            WHERE seller_id = CAST(:seller_id AS UUID) AND product_id = CAST(:product_id AS UUID)
              AND snapshot_date = (SELECT MAX(snapshot_date) FROM inventory_snapshots WHERE seller_id = CAST(:seller_id AS UUID) AND product_id = CAST(:product_id AS UUID))
            GROUP BY product_id
        ),
        roas_stats AS (
            SELECT product_id,
                   CASE WHEN SUM(ad_spend) > 0 THEN ROUND(SUM(revenue_from_ads) / SUM(ad_spend), 2) ELSE 0 END AS roas,
                   SUM(ad_spend) AS total_ad_spend,
                   SUM(revenue_from_ads) AS total_ad_revenue,
                   SUM(impressions) AS total_impressions,
                   SUM(clicks) AS total_clicks,
                   CASE WHEN SUM(impressions) > 0 THEN ROUND(SUM(clicks) * 100.0 / SUM(impressions), 2) ELSE 0 END AS ctr_pct,
                   CASE WHEN SUM(clicks) > 0 THEN ROUND(SUM(ad_spend) / SUM(clicks), 2) ELSE 0 END AS cost_per_click
            FROM traffic_metrics
            WHERE seller_id = CAST(:seller_id AS UUID) AND product_id = CAST(:product_id AS UUID)
            GROUP BY product_id
        ),
        rto_stats AS (
            SELECT COUNT(*) AS total_shipments,
                   COUNT(*) FILTER (WHERE rto_flag = true) AS rto_count,
                   ROUND(COUNT(*) FILTER (WHERE rto_flag = true) * 100.0 / NULLIF(COUNT(*), 0), 1) AS rto_rate_pct,
                   ROUND(AVG(CASE WHEN actual_delivery IS NOT NULL AND dispatch_date IS NOT NULL
                       THEN actual_delivery - dispatch_date END), 1) AS avg_delivery_days
            FROM logistics_metrics
            WHERE seller_id = CAST(:seller_id AS UUID)
              AND order_id IN (SELECT order_id FROM orders WHERE product_id = CAST(:product_id AS UUID) AND seller_id = CAST(:seller_id AS UUID))
        )
        SELECT p.product_name, p.sku, p.category, p.marketplace, p.brand, p.sub_category,
               COALESCE(r.total_revenue, 0) AS total_revenue,
               COALESCE(r.total_orders, 0) AS total_orders,
               COALESCE(r.avg_order_value, 0) AS avg_order_value,
               COALESCE(r.discounted_orders, 0) AS discounted_orders,
               COALESCE(r.total_discount_given, 0) AS total_discount_given,
               COALESCE(r.total_shipping_collected, 0) AS total_shipping_collected,
               COALESCE(ret.total_returns, 0) AS total_returns,
               COALESCE(ret.return_rate_pct, 0) AS return_rate_pct,
               COALESCE(s.stock_level, 0) AS stock_level,
               COALESCE(s.reserved_stock, 0) AS reserved_stock,
               COALESCE(s.reorder_threshold, 0) AS reorder_threshold,
               COALESCE(s.days_of_stock, 0) AS days_of_stock,
               COALESCE(ro.roas, 0) AS roas,
               COALESCE(ro.total_ad_spend, 0) AS total_ad_spend,
               COALESCE(ro.total_ad_revenue, 0) AS total_ad_revenue,
               COALESCE(ro.total_impressions, 0) AS total_impressions,
               COALESCE(ro.total_clicks, 0) AS total_clicks,
               COALESCE(ro.ctr_pct, 0) AS ctr_pct,
               COALESCE(ro.cost_per_click, 0) AS cost_per_click,
               COALESCE(rto.rto_count, 0) AS rto_count,
               COALESCE(rto.rto_rate_pct, 0) AS rto_rate_pct,
               COALESCE(rto.avg_delivery_days, 0) AS avg_delivery_days
        FROM products p
        LEFT JOIN revenue_stats r ON r.product_id = p.product_id
        LEFT JOIN return_stats ret ON ret.product_id = p.product_id
        LEFT JOIN stock_stats s ON s.product_id = p.product_id
        LEFT JOIN roas_stats ro ON ro.product_id = p.product_id
        CROSS JOIN rto_stats rto
        WHERE p.product_id = CAST(:product_id AS UUID) AND p.seller_id = CAST(:seller_id AS UUID)
    """)
    result = await db.execute(metrics_sql, {"product_id": product_id, "seller_id": seller_id})
    product_info = result.mappings().first()
    if not product_info:
        return {"status": "error", "message": "Product not found"}

    # ── 2. Per-marketplace pricing breakdown ──
    pricing_sql = text("""
        SELECT marketplace, selling_price, cost_price, mrp, commission_pct, 
               commission_amount, discount_percentage,
               CASE WHEN selling_price > 0 AND cost_price IS NOT NULL
                    THEN ROUND(((selling_price - cost_price - COALESCE(commission_amount, 0)) / selling_price) * 100, 1)
                    ELSE 0 END AS margin_pct,
               CASE WHEN selling_price > 0 AND cost_price IS NOT NULL
                    THEN ROUND(selling_price - cost_price - COALESCE(commission_amount, 0), 2)
                    ELSE 0 END AS net_profit_per_unit
        FROM pricing_snapshots
        WHERE seller_id = CAST(:seller_id AS UUID) AND product_id = CAST(:product_id AS UUID)
          AND snapshot_date = (SELECT MAX(snapshot_date) FROM pricing_snapshots WHERE seller_id = CAST(:seller_id AS UUID) AND product_id = CAST(:product_id AS UUID))
    """)
    pricing_result = await db.execute(pricing_sql, {"product_id": product_id, "seller_id": seller_id})
    pricing_rows = [dict(r) for r in pricing_result.mappings().all()]

    # ── 3. Per-marketplace revenue split ──
    mp_revenue_sql = text("""
        SELECT marketplace,
               SUM(selling_price * quantity) AS revenue,
               COUNT(*) AS orders,
               ROUND(AVG(selling_price * quantity), 2) AS aov,
               SUM(CASE WHEN return_flag = true THEN 1 ELSE 0 END) AS returns
        FROM orders
        WHERE seller_id = CAST(:seller_id AS UUID) AND product_id = CAST(:product_id AS UUID)
        GROUP BY marketplace
        ORDER BY revenue DESC
    """)
    mp_result = await db.execute(mp_revenue_sql, {"product_id": product_id, "seller_id": seller_id})
    marketplace_splits = [dict(r) for r in mp_result.mappings().all()]

    # Convert Decimal values to float for JSON serializability
    from decimal import Decimal
    def clean(obj):
        if isinstance(obj, dict):
            return {k: clean(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [clean(v) for v in obj]
        elif isinstance(obj, Decimal):
            return float(obj)
        return obj

    product_data = clean(dict(product_info))
    product_data["product_id"] = product_id
    product_data["pricing_by_marketplace"] = clean(pricing_rows)
    product_data["revenue_by_marketplace"] = clean(marketplace_splits)

    # Mark as running or create pending record
    # For now, just trigger it and wait (or background it)
    ai_result = await trigger_product_analysis(seller_id, product_id, product_data)
    
    if ai_result and ai_result.get("status") == "success":
        result_data = ai_result.get("result", {})
        
        # Save to database
        from sqlalchemy.dialects.postgresql import insert as pg_insert
        
        stmt = pg_insert(AIProductAnalysis).values(
            seller_id=seller_id,
            product_id=product_id,
            analysis_date=date.today(),
            product_metrics=product_data,
            executive_summary=result_data, # Use the synthesizer output
            status="completed"
        ).on_conflict_do_update(
            index_elements=["seller_id", "product_id", "analysis_date"],
            set_={
                "executive_summary": result_data,
                "status": "completed",
                "product_metrics": product_data,
                "updated_at": text("NOW()")
            }
        )
        await db.execute(stmt)
        await db.commit()
        
        return {"status": "success", "product_id": product_id, "result": result_data}
        
    from fastapi import HTTPException
    raise HTTPException(status_code=500, detail="AI Agent failed to analyze the product. Please check AI service logs.")


@router.get("/analysis/{product_id}", summary="Retrieve cached analysis result")
async def get_product_analysis(
    product_id: str,
    seller_id: str,
    db: AsyncSession = Depends(get_db),
    _scope: str = Depends(enforce_seller_scope),
):
    """
    Returns the latest cached AI analysis for a product.
    """
    sql = text("""
        SELECT *
        FROM ai_product_analyses
        WHERE product_id = :product_id AND seller_id = :seller_id
        ORDER BY analysis_date DESC
        LIMIT 1
    """)
    result = await db.execute(sql, {"product_id": product_id, "seller_id": seller_id})
    row = result.mappings().first()
    
    if not row:
        return {"status": "not_found", "message": "No analysis found for this product."}
        
    d = dict(row)
    d['id'] = str(d['id'])
    d['product_id'] = str(d['product_id'])
    d['seller_id'] = str(d['seller_id'])
    if d['analysis_date']:
        d['analysis_date'] = str(d['analysis_date'])
    if d['created_at']:
        d['created_at'] = str(d['created_at'])
    if d['updated_at']:
        d['updated_at'] = str(d['updated_at'])
        
    return {"status": "success", "data": d}
