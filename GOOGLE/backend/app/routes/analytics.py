"""Analytics routes — GET /analytics/*"""
import time
from collections import defaultdict
from fastapi import APIRouter, Depends, Query, HTTPException
from pydantic import BaseModel, Field
from typing import List

from app.core.security import enforce_seller_scope
from app.clients import bigquery_client as bq
from app.services import analytics_queries as q

router = APIRouter(prefix="/analytics", tags=["analytics"])

# In-memory stores for immediate feedback (no BigQuery streaming lag).
# BigQuery is the source of truth; these bridge the gap until DML propagates.
#
# _restock_store entries expire after _RESTOCK_TTL_S seconds — by that point
# BigQuery has absorbed the DML UPDATE and bq_stock already reflects the addition.
# Keeping the delta past the TTL would double-count it.
_RESTOCK_TTL_S  = 8    # BQ DML UPDATE propagates in ~1-3 s; 8 s is safe headroom
_PURCHASE_TTL_S = 300  # BQ streaming insert can take up to ~5 min; 5 min headroom

_restock_store:  dict[str, dict[str, tuple[int, float]]] = defaultdict(dict)
_purchase_store: dict[str, dict[str, tuple[int, float]]] = defaultdict(dict)


def _restock_delta(seller_id: str, product_id: str) -> int:
    """Return the transient restock delta that has not yet been absorbed by BQ."""
    entry = _restock_store.get(seller_id, {}).get(product_id)
    if not entry:
        return 0
    qty, ts = entry
    if time.time() - ts > _RESTOCK_TTL_S:
        _restock_store[seller_id].pop(product_id, None)
        return 0
    return qty


def _purchase_delta(seller_id: str, product_id: str) -> int:
    """Return the transient purchase deduction that has not yet been absorbed by BQ."""
    entry = _purchase_store.get(seller_id, {}).get(product_id)
    if not entry:
        return 0
    qty, ts = entry
    if time.time() - ts > _PURCHASE_TTL_S:
        _purchase_store[seller_id].pop(product_id, None)
        return 0
    return qty


def _effective_stock(bq_stock: int, product_id: str, seller_id: str) -> int:
    """BQ stock + transient restock delta − transient purchase deduction."""
    restock  = _restock_delta(seller_id, product_id)
    purchase = _purchase_delta(seller_id, product_id)
    return max(0, bq_stock + restock - purchase)


def _recommendation_label(
    stock: int, demand_score: float, views: int, purchase_events: int, conv_pct: float
) -> str:
    """Mirror the CASE logic in RECOMMENDATIONS_SQL so labels match effective stock."""
    if stock <= 2 and demand_score >= 1:    return "RESTOCK_URGENT"
    if stock <= 4 and demand_score >= 0.5:  return "RESTOCK_SOON"
    if views >= 5 and conv_pct >= 20:       return "INCREASE_PRICE"
    if views >= 4 and conv_pct < 5:         return "DISCOUNT"
    if views < 2 and purchase_events == 0:  return "DONT_RESTOCK"
    return "MAINTAIN"


class RestockRequest(BaseModel):
    seller_id:  str
    product_id: str
    quantity:   int = Field(..., ge=1, le=500)


class PurchaseItem(BaseModel):
    product_id: str
    quantity:   int = Field(..., ge=1)


class PurchaseRequest(BaseModel):
    seller_id: str
    items: List[PurchaseItem]


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
        traffic = await bq.query(
            q.STOREFRONT_HOURLY_TRAFFIC_SQL,
            {"seller_id": seller_id, "hours": days * 24},
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
    rows = await bq.query(q.PRODUCT_STOCK_SQL, {"seller_id": seller_id})
    products = []
    for row in rows:
        products.append({
            **row,
            "current_stock": _effective_stock(int(row["current_stock"]), row["product_id"], seller_id),
        })
    return {"seller_id": seller_id, "products": products}


@router.post("/stock/purchase")
async def record_purchase(body: PurchaseRequest):
    """Storefront calls this at checkout — immediate stock deduction, no BigQuery lag."""
    now = time.time()
    store = _purchase_store[body.seller_id]
    for item in body.items:
        prev_qty, prev_ts = store.get(item.product_id, (0, 0.0))
        if now - prev_ts <= _PURCHASE_TTL_S:
            new_qty = prev_qty + item.quantity
        else:
            new_qty = item.quantity
        store[item.product_id] = (new_qty, now)
    return {"ok": True}


@router.post("/stock/restock")
async def restock_product(body: RestockRequest):
    """Add stock. Writes to BigQuery so it survives server restarts."""
    rows = await bq.query(q.PRODUCT_STOCK_SQL, {"seller_id": body.seller_id})
    product_row = next((r for r in rows if r["product_id"] == body.product_id), None)
    if not product_row:
        raise HTTPException(status_code=404, detail="Product not found")

    # Persist to BigQuery — let errors surface so the frontend knows the write failed.
    await bq.query(q.RESTOCK_SQL, {
        "product_id": body.product_id,
        "seller_id":  body.seller_id,
        "quantity":   body.quantity,
    })

    # Record a transient delta that expires once BQ DML propagates (_RESTOCK_TTL_S).
    prev_qty, prev_ts = _restock_store[body.seller_id].get(body.product_id, (0, 0.0))
    if time.time() - prev_ts <= _RESTOCK_TTL_S:
        new_qty = prev_qty + body.quantity
    else:
        new_qty = body.quantity
    _restock_store[body.seller_id][body.product_id] = (new_qty, time.time())

    new_stock = _effective_stock(int(product_row["current_stock"]), body.product_id, body.seller_id)
    return {
        "ok": True,
        "product_id":     body.product_id,
        "quantity_added": body.quantity,
        "updated": {**product_row, "current_stock": new_stock},
    }


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
        eff_stock = _effective_stock(int(row.get("current_stock", 0)), row["product_id"], seller_id)
        label = _recommendation_label(
            stock=eff_stock,
            demand_score=float(row.get("demand_score") or 0),
            views=int(row.get("views") or 0),
            purchase_events=int(row.get("purchase_events") or 0),
            conv_pct=float(row.get("conversion_pct") or 0),
        )
        enriched.append({
            **row,
            "current_stock":     eff_stock,
            "recommendation":    label,
            "ai_insight":        insight.get("insight"),
            "ai_urgency":        insight.get("urgency"),
            "ai_revenue_impact": insight.get("monthly_revenue_impact"),
        })

    return {
        "seller_id":      seller_id,
        "period_days":    days,
        "ai_powered":     bool(ai_insights),
        "recommendations": enriched,
    }
