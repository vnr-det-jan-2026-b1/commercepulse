"""Analytics routes — GET /analytics/*"""
from fastapi import APIRouter, Depends, Query

from app.core.security import enforce_seller_scope
from app.clients import bigquery_client as bq
from app.services import analytics_queries as q

router = APIRouter(prefix="/analytics", tags=["analytics"])


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
