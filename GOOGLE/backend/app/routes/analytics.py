"""Analytics routes — GET /analytics/*"""
from collections import defaultdict
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field

from app.core.security import enforce_seller_scope
from app.clients import bigquery_client as bq
from app.services import analytics_queries as q

router = APIRouter(prefix="/analytics", tags=["analytics"])

# In-memory restock store: seller_id → { product_id: total_units_added }
# Persists for the lifetime of the server process. Avoids BigQuery DML entirely.
_restock_store: dict[str, dict[str, int]] = defaultdict(dict)


class RestockRequest(BaseModel):
    seller_id: str
    product_id: str
    quantity: int = Field(..., ge=1, le=10000)


@router.get("/dashboard")
async def dashboard(
    seller_id: str = Query(...),
    _scope:    str = Depends(enforce_seller_scope),
):
    row = await bq.query_single(q.DASHBOARD_SQL, {"seller_id": seller_id})
    return {
        "seller_id": seller_id,
        "kpis": {
            "total_net_revenue":     float(row.get("total_net_revenue") or 0),
            "total_orders":          int(row.get("total_orders") or 0),
            "cancellation_rate_pct": float(row.get("cancellation_rate_pct") or 0),
            "returned_orders":       int(row.get("returned_orders") or 0),
            "low_stock_products":    int(row.get("low_stock_count") or 0),
            "stockout_products":     int(row.get("stockout_count") or 0),
            "rto_rate_pct":          float(row.get("rto_rate_pct") or 0),
            "avg_roas":              float(row.get("avg_roas") or 0),
        } if row else {},
    }


@router.get("/revenue")
async def revenue_summary(
    seller_id: str = Query(...),
    days:      int = Query(30, ge=1, le=365),
    _scope:    str = Depends(enforce_seller_scope),
):
    rows = await bq.query(q.REVENUE_SQL, {"seller_id": seller_id, "days": days})
    return {"seller_id": seller_id, "period_days": days, "data": rows}


@router.get("/orders/trend")
async def orders_trend(
    seller_id: str = Query(...),
    days:      int = Query(30, ge=1, le=365),
    _scope:    str = Depends(enforce_seller_scope),
):
    rows = await bq.query(q.ORDERS_TREND_SQL, {"seller_id": seller_id, "days": days})
    return {"seller_id": seller_id, "period_days": days, "data": rows}


@router.get("/funnel")
async def traffic_funnel(
    seller_id: str = Query(...),
    days:      int = Query(7, ge=1, le=90),
    _scope:    str = Depends(enforce_seller_scope),
):
    per_product = await bq.query(q.TRAFFIC_FUNNEL_SQL, {"seller_id": seller_id, "days": days})
    overall     = await bq.query(q.FUNNEL_OVERALL_SQL,  {"seller_id": seller_id, "days": days})
    return {
        "seller_id":   seller_id,
        "period_days": days,
        "overall_trend": overall,
        "by_product":    per_product,
    }


@router.get("/inventory/alerts")
async def inventory_alerts(
    seller_id: str = Query(...),
    _scope:    str = Depends(enforce_seller_scope),
):
    rows = await bq.query(q.INVENTORY_ALERTS_SQL, {"seller_id": seller_id})
    return {"seller_id": seller_id, "alert_count": len(rows), "alerts": rows}


@router.get("/inventory/status")
async def inventory_status(
    seller_id: str = Query(...),
    _scope:    str = Depends(enforce_seller_scope),
):
    rows = await bq.query(q.INVENTORY_STATUS_SQL, {"seller_id": seller_id})
    return {"seller_id": seller_id, "count": len(rows), "data": rows}


@router.get("/pricing/margins")
async def pricing_margins(
    seller_id: str = Query(...),
    _scope:    str = Depends(enforce_seller_scope),
):
    rows = await bq.query(q.PRICING_MARGINS_SQL, {"seller_id": seller_id})
    return {"seller_id": seller_id, "count": len(rows), "data": rows}


@router.get("/logistics/rto-rate")
async def logistics_rto_rate(
    seller_id: str = Query(...),
    days:      int = Query(30, ge=1, le=365),
    _scope:    str = Depends(enforce_seller_scope),
):
    rows = await bq.query(q.LOGISTICS_RTO_SQL, {"seller_id": seller_id, "days": days})
    return {"seller_id": seller_id, "period_days": days, "data": rows}


@router.get("/storefront")
async def storefront_analytics(
    seller_id:   str = Query(...),
    days:        int = Query(7, ge=1, le=90),
    granularity: str = Query("day", pattern="^(day|hour)$"),
    _scope:      str = Depends(enforce_seller_scope),
):
    params = {"seller_id": seller_id, "days": days}

    if granularity == "hour":
        hours_count = days * 24
        traffic = await bq.query(
            q.STOREFRONT_HOURLY_TRAFFIC_SQL,
            {"seller_id": seller_id, "hours": hours_count},
        )
    else:
        traffic = await bq.query(q.STOREFRONT_DAILY_TRAFFIC_SQL, params)

    overview   = await bq.query_single(q.STOREFRONT_OVERVIEW_SQL, params)
    products   = await bq.query(q.STOREFRONT_PRODUCTS_SQL,        params)
    funnel_row = await bq.query_single(q.STOREFRONT_FUNNEL_SQL,   params)
    return {
        "seller_id":     seller_id,
        "period_days":   days,
        "granularity":   granularity,
        "traffic":       traffic,
        "overview":      overview or {},
        "products":      products,
        "funnel":        funnel_row or {},
    }


@router.get("/stock")
async def product_stock(
    seller_id: str = Query(...),
    _scope:    str = Depends(enforce_seller_scope),
):
    MAX_STOCK = 10
    rows = await bq.query(q.PRODUCT_STOCK_SQL, {"seller_id": seller_id})
    adjustments = _restock_store.get(seller_id, {})
    products = []
    for row in rows:
        extra = adjustments.get(row["product_id"], 0)
        products.append({
            **row,
            "current_stock": min(row["current_stock"] + extra, MAX_STOCK),
        })
    return {"seller_id": seller_id, "products": products}


@router.post("/stock/restock")
async def restock_product(body: RestockRequest):
    MAX_STOCK = 10
    rows = await bq.query(q.PRODUCT_STOCK_SQL, {"seller_id": body.seller_id})
    product_row = next((r for r in rows if r["product_id"] == body.product_id), None)
    if not product_row:
        raise HTTPException(status_code=404, detail="Product not found")

    store = _restock_store[body.seller_id]
    current = min(product_row["current_stock"] + store.get(body.product_id, 0), MAX_STOCK)
    space   = MAX_STOCK - current
    if space <= 0:
        raise HTTPException(status_code=400, detail="Stock is already at maximum (10 units)")
    allowed = min(body.quantity, space)

    store[body.product_id] = store.get(body.product_id, 0) + allowed
    updated = {**product_row, "current_stock": current + allowed}
    return {"ok": True, "product_id": body.product_id, "quantity_added": allowed, "updated": updated}


@router.get("/products")
async def list_products(
    seller_id: str = Query(...),
    _scope:    str = Depends(enforce_seller_scope),
):
    rows = await bq.query(q.PRODUCTS_SQL, {"seller_id": seller_id})
    return {"seller_id": seller_id, "products": rows}


@router.get("/recommendations")
async def product_recommendations(
    seller_id: str = Query(...),
    days:      int = Query(7, ge=1, le=90),
    ai:        bool = Query(True),
    _scope:    str = Depends(enforce_seller_scope),
):
    import logging
    logger = logging.getLogger(__name__)
    rows = await bq.query(q.RECOMMENDATIONS_SQL, {"seller_id": seller_id, "days": days})

    ai_insights: dict = {}
    if ai and rows:
        try:
            from app.services import gemini_service as gemini
            ai_insights = await gemini.generate_product_insights(seller_id, rows)
        except Exception as e:
            logger.warning("Gemini insights skipped: %s", e)

    enriched = []
    for row in rows:
        insight = ai_insights.get(row["product_id"], {})
        enriched.append({
            **row,
            "ai_insight": insight.get("insight"),
            "ai_urgency": insight.get("urgency"),
            "ai_revenue_impact": insight.get("monthly_revenue_impact"),
        })

    return {
        "seller_id": seller_id,
        "period_days": days,
        "ai_powered": bool(ai_insights),
        "recommendations": enriched,
    }
