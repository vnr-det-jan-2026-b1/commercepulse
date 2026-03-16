"""Analytics routes — GET /analytics/*"""
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field

from app.core.security import enforce_seller_scope
from app.clients import bigquery_client as bq
from app.services import analytics_queries as q

router = APIRouter(prefix="/analytics", tags=["analytics"])


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
    rows = await bq.query(q.PRODUCT_STOCK_SQL, {"seller_id": seller_id})
    return {"seller_id": seller_id, "products": rows}


@router.post("/stock/restock")
async def restock_product(body: RestockRequest):
    await bq.query(q.RESTOCK_SQL, {
        "seller_id":  body.seller_id,
        "product_id": body.product_id,
        "quantity":   body.quantity,
    })
    # Return updated stock for this product
    rows = await bq.query(q.PRODUCT_STOCK_SQL, {"seller_id": body.seller_id})
    updated = next((r for r in rows if r["product_id"] == body.product_id), None)
    return {"ok": True, "product_id": body.product_id, "quantity_added": body.quantity, "updated": updated}


@router.get("/recommendations")
async def product_recommendations(
    seller_id: str = Query(...),
    days:      int = Query(7, ge=1, le=90),
    _scope:    str = Depends(enforce_seller_scope),
):
    rows = await bq.query(q.RECOMMENDATIONS_SQL, {"seller_id": seller_id, "days": days})
    return {"seller_id": seller_id, "period_days": days, "recommendations": rows}
