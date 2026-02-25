"""Analytics routes — GET /analytics/*"""
from datetime import date, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.core.security import enforce_seller_scope

router = APIRouter()


# ── Revenue Summary ────────────────────────────────────────────
@router.get("/revenue", summary="Revenue summary for a seller")
async def revenue_summary(
    seller_id: str,
    days:      int = Query(30, ge=1, le=365, description="Lookback window in days"),
    db:        AsyncSession = Depends(get_db),
    _scope:    str = Depends(enforce_seller_scope),
):
    since = date.today() - timedelta(days=days)
    sql = text("""
        SELECT
            marketplace,
            SUM(selling_price * quantity)                          AS gross_revenue,
            SUM(net_revenue)                                       AS net_revenue,
            SUM(discount)                                          AS total_discount,
            COUNT(*)                                               AS total_orders,
            COUNT(*) FILTER (WHERE order_status = 'delivered')     AS delivered_orders,
            COUNT(*) FILTER (WHERE order_status = 'cancelled')     AS cancelled_orders,
            COUNT(*) FILTER (WHERE return_flag = TRUE)             AS returned_orders,
            ROUND(AVG(selling_price)::numeric, 2)                  AS avg_order_value
        FROM orders
        WHERE seller_id = :seller_id
          AND order_date >= :since
        GROUP BY marketplace
        ORDER BY gross_revenue DESC
    """)
    result = await db.execute(sql, {"seller_id": seller_id, "since": since})
    rows = result.mappings().all()
    return {
        "seller_id": seller_id,
        "period_days": days,
        "since": str(since),
        "data": [dict(r) for r in rows],
    }


# ── Orders Summary (trend by day) ──────────────────────────────
@router.get("/orders/trend", summary="Daily order trend")
async def orders_trend(
    seller_id: str,
    days:      int = Query(30, ge=1, le=365),
    db:        AsyncSession = Depends(get_db),
    _scope:    str = Depends(enforce_seller_scope),
):
    since = date.today() - timedelta(days=days)
    sql = text("""
        SELECT
            order_date,
            COUNT(*)                                           AS total_orders,
            SUM(selling_price * quantity)                      AS revenue,
            COUNT(*) FILTER (WHERE order_status = 'delivered') AS delivered,
            COUNT(*) FILTER (WHERE order_status = 'cancelled') AS cancelled
        FROM orders
        WHERE seller_id = :seller_id AND order_date >= :since
        GROUP BY order_date
        ORDER BY order_date
    """)
    result = await db.execute(sql, {"seller_id": seller_id, "since": since})
    rows = result.mappings().all()
    return {"seller_id": seller_id, "data": [dict(r) for r in rows]}


# ── Inventory Alerts ───────────────────────────────────────────
@router.get("/inventory/alerts", summary="Low-stock and stockout alerts")
async def inventory_alerts(
    seller_id: str,
    db:        AsyncSession = Depends(get_db),
    _scope:    str = Depends(enforce_seller_scope),
):
    sql = text("""
        SELECT
            p.sku,
            p.product_name,
            p.category,
            i.marketplace,
            i.available_stock,
            i.reserved_stock,
            i.reorder_threshold,
            i.days_of_stock,
            i.warehouse_location,
            i.snapshot_date,
            CASE
                WHEN i.available_stock = 0 THEN 'STOCKOUT'
                WHEN i.available_stock <= i.reorder_threshold THEN 'LOW STOCK'
                ELSE 'OK'
            END AS alert_level
        FROM inventory_snapshots i
        JOIN products p ON p.product_id = i.product_id
        WHERE i.seller_id = :seller_id
          AND i.snapshot_date = (
              SELECT MAX(snapshot_date) FROM inventory_snapshots
              WHERE seller_id = :seller_id
          )
          AND i.available_stock <= i.reorder_threshold
        ORDER BY i.available_stock ASC
    """)
    result = await db.execute(sql, {"seller_id": seller_id})
    rows = result.mappings().all()
    return {
        "seller_id": seller_id,
        "alert_count": len(rows),
        "alerts": [dict(r) for r in rows],
    }


# ── Inventory Status (full latest snapshot) ────────────────────
@router.get("/inventory/status", summary="Current inventory status")
async def inventory_status(
    seller_id: str,
    db:        AsyncSession = Depends(get_db),
    _scope:    str = Depends(enforce_seller_scope),
):
    sql = text("""
        SELECT
            p.sku, p.product_name, p.category,
            i.marketplace, i.available_stock, i.reserved_stock,
            i.total_stock, i.reorder_threshold, i.days_of_stock, i.snapshot_date
        FROM inventory_snapshots i
        JOIN products p ON p.product_id = i.product_id
        WHERE i.seller_id = :seller_id
          AND i.snapshot_date = (
              SELECT MAX(snapshot_date) FROM inventory_snapshots WHERE seller_id = :seller_id
          )
        ORDER BY i.available_stock ASC
    """)
    result = await db.execute(sql, {"seller_id": seller_id})
    rows = result.mappings().all()
    return {"seller_id": seller_id, "count": len(rows), "data": [dict(r) for r in rows]}


# ── Pricing Margins ────────────────────────────────────────────
@router.get("/pricing/margins", summary="Current pricing and margin analysis")
async def pricing_margins(
    seller_id: str,
    db:        AsyncSession = Depends(get_db),
    _scope:    str = Depends(enforce_seller_scope),
):
    sql = text("""
        SELECT
            p.sku, p.product_name, p.category,
            pr.marketplace, pr.selling_price, pr.cost_price, pr.mrp,
            pr.commission_pct, pr.commission_amount, pr.discount_percentage,
            pr.net_margin, pr.margin_pct, pr.snapshot_date
        FROM pricing_snapshots pr
        JOIN products p ON p.product_id = pr.product_id
        WHERE pr.seller_id = :seller_id
          AND pr.snapshot_date = (
              SELECT MAX(snapshot_date) FROM pricing_snapshots WHERE seller_id = :seller_id
          )
        ORDER BY pr.margin_pct ASC NULLS LAST
    """)
    result = await db.execute(sql, {"seller_id": seller_id})
    rows = result.mappings().all()
    return {"seller_id": seller_id, "count": len(rows), "data": [dict(r) for r in rows]}


# ── Traffic Funnel ─────────────────────────────────────────────
@router.get("/traffic/funnel", summary="Traffic funnel and ROAS overview")
async def traffic_funnel(
    seller_id: str,
    days:      int = Query(7, ge=1, le=90),
    db:        AsyncSession = Depends(get_db),
    _scope:    str = Depends(enforce_seller_scope),
):
    since = date.today() - timedelta(days=days)
    sql = text("""
        SELECT
            p.sku, p.product_name, p.category,
            t.marketplace,
            SUM(t.impressions)       AS total_impressions,
            SUM(t.clicks)            AS total_clicks,
            SUM(t.add_to_cart)       AS total_add_to_cart,
            SUM(t.orders)            AS total_orders,
            ROUND(
                CASE WHEN SUM(t.impressions) > 0
                    THEN SUM(t.clicks)::numeric / SUM(t.impressions) * 100 END, 2
            ) AS ctr_pct,
            ROUND(
                CASE WHEN SUM(t.clicks) > 0
                    THEN SUM(t.orders)::numeric / SUM(t.clicks) * 100 END, 2
            ) AS conversion_rate_pct,
            SUM(t.ad_spend)          AS total_ad_spend,
            SUM(t.revenue_from_ads)  AS total_revenue_from_ads,
            ROUND(
                CASE WHEN SUM(t.ad_spend) > 0
                    THEN SUM(t.revenue_from_ads) / SUM(t.ad_spend) END, 2
            ) AS roas
        FROM traffic_metrics t
        JOIN products p ON p.product_id = t.product_id
        WHERE t.seller_id = :seller_id AND t.metric_date >= :since
        GROUP BY p.sku, p.product_name, p.category, t.marketplace
        ORDER BY roas DESC NULLS LAST
    """)
    result = await db.execute(sql, {"seller_id": seller_id, "since": since})
    rows = result.mappings().all()
    return {
        "seller_id": seller_id, "period_days": days,
        "count": len(rows), "data": [dict(r) for r in rows],
    }


# ── Logistics RTO Rate ─────────────────────────────────────────
@router.get("/logistics/rto-rate", summary="RTO rate and delivery performance")
async def logistics_rto_rate(
    seller_id: str,
    days:      int = Query(30, ge=1, le=365),
    db:        AsyncSession = Depends(get_db),
    _scope:    str = Depends(enforce_seller_scope),
):
    since = date.today() - timedelta(days=days)
    sql = text("""
        SELECT
            marketplace,
            COUNT(*)                                      AS total_shipments,
            COUNT(*) FILTER (WHERE rto_flag = TRUE)       AS rto_count,
            ROUND(
                COUNT(*) FILTER (WHERE rto_flag = TRUE)::numeric / NULLIF(COUNT(*), 0) * 100, 2
            )                                             AS rto_rate_pct,
            COUNT(*) FILTER (WHERE delivery_status = 'delivered') AS delivered,
            ROUND(AVG(shipping_time_days)::numeric, 1)   AS avg_shipping_days,
            fulfillment_type
        FROM logistics_metrics
        WHERE seller_id = :seller_id AND snapshot_date >= :since
        GROUP BY marketplace, fulfillment_type
        ORDER BY rto_rate_pct DESC NULLS LAST
    """)
    result = await db.execute(sql, {"seller_id": seller_id, "since": since})
    rows = result.mappings().all()
    return {
        "seller_id": seller_id, "period_days": days,
        "data": [dict(r) for r in rows],
    }


# ── Executive Dashboard (single call, all KPIs) ────────────────
@router.get("/dashboard", summary="All key metrics in one call")
async def dashboard(
    seller_id: str,
    days:      int = Query(30, ge=1, le=365),
    db:        AsyncSession = Depends(get_db),
    _scope:    str = Depends(enforce_seller_scope),
):
    since = date.today() - timedelta(days=days)

    revenue_sql = text("""
        SELECT
            COALESCE(SUM(net_revenue), 0)                                            AS total_net_revenue,
            COUNT(*)                                                                  AS total_orders,
            COUNT(*) FILTER (WHERE order_status = 'cancelled')                       AS cancelled_orders,
            ROUND(
                COUNT(*) FILTER (WHERE order_status = 'cancelled')::numeric
                / NULLIF(COUNT(*), 0) * 100, 2
            )                                                                         AS cancellation_rate_pct,
            COUNT(*) FILTER (WHERE return_flag = TRUE)                               AS returned_orders
        FROM orders
        WHERE seller_id = :seller_id AND order_date >= :since
    """)
    inv_sql = text("""
        SELECT COUNT(*) AS low_stock_count
        FROM inventory_snapshots
        WHERE seller_id = :seller_id
          AND snapshot_date = (SELECT MAX(snapshot_date) FROM inventory_snapshots WHERE seller_id = :seller_id)
          AND available_stock <= reorder_threshold
    """)
    rto_sql = text("""
        SELECT ROUND(
            COUNT(*) FILTER (WHERE rto_flag = TRUE)::numeric / NULLIF(COUNT(*), 0) * 100, 2
        ) AS rto_rate_pct
        FROM logistics_metrics
        WHERE seller_id = :seller_id AND snapshot_date >= :since
    """)
    roas_sql = text("""
        SELECT ROUND(
            CASE WHEN SUM(ad_spend) > 0 THEN SUM(revenue_from_ads) / SUM(ad_spend) END, 2
        ) AS avg_roas
        FROM traffic_metrics
        WHERE seller_id = :seller_id AND metric_date >= :since
    """)

    rev  = (await db.execute(revenue_sql, {"seller_id": seller_id, "since": since})).mappings().first()
    inv  = (await db.execute(inv_sql,     {"seller_id": seller_id})).mappings().first()
    rto  = (await db.execute(rto_sql,     {"seller_id": seller_id, "since": since})).mappings().first()
    roas = (await db.execute(roas_sql,    {"seller_id": seller_id, "since": since})).mappings().first()

    return {
        "seller_id":           seller_id,
        "period_days":         days,
        "kpis": {
            "total_net_revenue":    float(rev["total_net_revenue"] or 0),
            "total_orders":         int(rev["total_orders"] or 0),
            "cancellation_rate_pct":float(rev["cancellation_rate_pct"] or 0),
            "returned_orders":      int(rev["returned_orders"] or 0),
            "low_stock_products":   int(inv["low_stock_count"] or 0),
            "rto_rate_pct":         float(rto["rto_rate_pct"] or 0),
            "avg_roas":             float(roas["avg_roas"] or 0),
        },
    }
