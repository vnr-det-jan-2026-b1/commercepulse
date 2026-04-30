"""Analytics routes — GET /analytics/*

BigQuery is the single source of truth for stock. DML INSERT (purchases) and
DML UPDATE (restocks) are synchronous and immediately query-visible, so no
in-memory delta bridging is needed.
"""
import uuid
import logging
from fastapi import APIRouter, Depends, Query, HTTPException
from pydantic import BaseModel, Field
from typing import List

from app.core.security import enforce_seller_scope
from app.clients import bigquery_client as bq
from app.services import analytics_queries as q

router = APIRouter(prefix="/analytics", tags=["analytics"])
logger = logging.getLogger(__name__)


class RestockRequest(BaseModel):
    seller_id:  str
    product_id: str
    quantity:   int = Field(..., ge=1, le=500)


class PurchaseItem(BaseModel):
    product_id: str
    quantity:   int = Field(..., ge=1)


class PurchaseRequest(BaseModel):
    seller_id:  str
    session_id: str = ""
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
    return {
        "seller_id": seller_id,
        "products":  [{**row, "current_stock": int(row["current_stock"])} for row in rows],
    }


@router.post("/stock/purchase")
async def record_purchase(body: PurchaseRequest):
    """Storefront calls this at checkout — DML INSERT each item to storefront_events.

    DML INSERT is synchronous and immediately query-visible, so PRODUCT_STOCK_SQL
    reflects the deduction on the very next call.
    """
    catalog_rows = await bq.query(q.PRODUCTS_SQL, {"seller_id": body.seller_id})
    catalog = {r["product_id"]: r for r in catalog_rows}

    for item in body.items:
        product = catalog.get(item.product_id)
        if not product:
            raise HTTPException(status_code=404, detail=f"Product {item.product_id} not found")
        await bq.query(q.STOREFRONT_PURCHASE_INSERT_SQL, {
            "event_id":     str(uuid.uuid4()),
            "session_id":   body.session_id or f"checkout-{uuid.uuid4()}",
            "seller_id":    body.seller_id,
            "product_id":   item.product_id,
            "product_name": product["name"],
            "price":        float(product["price"]),
            "quantity":     item.quantity,
            "page_url":     "/checkout",
        })
    return {"ok": True}


@router.post("/stock/restock")
async def restock_product(body: RestockRequest):
    """Add stock via BQ DML UPDATE. Synchronous — visible to subsequent SELECTs immediately."""
    rows = await bq.query(q.PRODUCT_STOCK_SQL, {"seller_id": body.seller_id})
    if not any(r["product_id"] == body.product_id for r in rows):
        raise HTTPException(status_code=404, detail="Product not found")

    await bq.query(q.RESTOCK_SQL, {
        "product_id": body.product_id,
        "seller_id":  body.seller_id,
        "quantity":   body.quantity,
    })

    rows_after = await bq.query(q.PRODUCT_STOCK_SQL, {"seller_id": body.seller_id})
    updated = next((r for r in rows_after if r["product_id"] == body.product_id), None)
    return {
        "ok":             True,
        "product_id":     body.product_id,
        "quantity_added": body.quantity,
        "updated":        updated,
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
