"""
BigQuery Standard SQL queries for analytics endpoints.
Ported from AZURE PostgreSQL queries with BQ-compatible syntax:
  - FILTER (WHERE ...) → COUNTIF(...)
  - ::numeric CAST     → CAST(... AS FLOAT64)
  - NULLIF(x, 0)       → preserved (BQ compatible)
"""
from app.core.config import settings

G = settings.BQ_DATASET_GOLD
B = settings.BQ_DATASET_BRONZE


# ── Dashboard KPIs ─────────────────────────────────────────────

DASHBOARD_SQL = f"""
SELECT
  total_net_revenue,
  total_orders,
  cancellation_rate_pct,
  returned_orders,
  stockout_count,
  low_stock_count,
  rto_rate_pct,
  avg_roas,
  computed_at
FROM `{G}.seller_dashboard_kpis`
WHERE seller_id = @seller_id
LIMIT 1
"""


# ── Revenue Summary ────────────────────────────────────────────

REVENUE_SQL = f"""
SELECT
  marketplace,
  SUM(CAST(selling_price AS FLOAT64) * quantity)  AS gross_revenue,
  SUM(CAST(net_revenue AS FLOAT64))               AS net_revenue,
  SUM(CAST(discount AS FLOAT64))                  AS total_discount,
  COUNT(*)                                        AS total_orders,
  COUNTIF(order_status = 'delivered')             AS delivered_orders,
  COUNTIF(order_status = 'cancelled')             AS cancelled_orders,
  COUNTIF(return_flag)                            AS returned_orders,
  ROUND(AVG(CAST(selling_price AS FLOAT64)), 2)   AS avg_order_value
FROM `{B}.orders`
WHERE seller_id = @seller_id
  AND order_date >= DATE_SUB(CURRENT_DATE(), INTERVAL @days DAY)
GROUP BY marketplace
ORDER BY gross_revenue DESC
"""


# ── Orders Trend ───────────────────────────────────────────────

ORDERS_TREND_SQL = f"""
SELECT
  order_date,
  COUNT(*)                         AS total_orders,
  SUM(CAST(selling_price AS FLOAT64) * quantity) AS revenue,
  COUNTIF(order_status = 'delivered') AS delivered,
  COUNTIF(order_status = 'cancelled') AS cancelled
FROM `{B}.orders`
WHERE seller_id = @seller_id
  AND order_date >= DATE_SUB(CURRENT_DATE(), INTERVAL @days DAY)
GROUP BY order_date
ORDER BY order_date
"""


# ── Inventory Alerts ───────────────────────────────────────────

INVENTORY_ALERTS_SQL = f"""
SELECT
  sku,
  marketplace,
  available_stock,
  reserved_stock,
  reorder_threshold,
  days_until_stockout,
  recommended_reorder_qty,
  risk_level,
  score_date
FROM `{G}.inventory_risk_scores`
WHERE seller_id = @seller_id
  AND risk_level IN ('CRITICAL', 'HIGH')
ORDER BY
  CASE risk_level WHEN 'CRITICAL' THEN 0 WHEN 'HIGH' THEN 1 ELSE 2 END,
  days_until_stockout ASC
"""


# ── Inventory Status (full) ─────────────────────────────────────

INVENTORY_STATUS_SQL = f"""
SELECT
  sku,
  marketplace,
  available_stock,
  reserved_stock,
  reorder_threshold,
  days_of_stock,
  warehouse_location,
  snapshot_date
FROM `{B}.inventory_snapshots`
WHERE seller_id = @seller_id
  AND snapshot_date = (
    SELECT MAX(snapshot_date) FROM `{B}.inventory_snapshots`
    WHERE seller_id = @seller_id
  )
ORDER BY available_stock ASC
"""


# ── Pricing Margins ────────────────────────────────────────────

PRICING_MARGINS_SQL = f"""
SELECT
  sku,
  marketplace,
  selling_price,
  cost_price,
  mrp,
  commission_pct,
  commission_amount,
  discount_percentage,
  net_margin,
  margin_pct,
  snapshot_date
FROM `{B}.pricing_snapshots`
WHERE seller_id = @seller_id
  AND snapshot_date = (
    SELECT MAX(snapshot_date) FROM `{B}.pricing_snapshots`
    WHERE seller_id = @seller_id
  )
ORDER BY margin_pct ASC
"""


# ── Traffic Funnel ─────────────────────────────────────────────

TRAFFIC_FUNNEL_SQL = f"""
SELECT
  sku,
  marketplace,
  SUM(impressions)                                          AS total_impressions,
  SUM(clicks)                                              AS total_clicks,
  SUM(add_to_cart)                                         AS total_add_to_cart,
  SUM(purchases)                                           AS total_purchases,
  ROUND(SAFE_DIVIDE(SUM(clicks), NULLIF(SUM(impressions), 0)) * 100, 2) AS ctr_pct,
  ROUND(SAFE_DIVIDE(SUM(purchases), NULLIF(SUM(clicks), 0)) * 100, 2)  AS conversion_rate_pct,
  ROUND(SAFE_DIVIDE(SUM(add_to_cart), NULLIF(SUM(clicks), 0)) * 100, 2) AS click_to_cart_pct,
  SUM(ad_spend)                                            AS total_ad_spend,
  SUM(revenue_from_ads)                                    AS total_revenue_from_ads,
  ROUND(SAFE_DIVIDE(SUM(revenue_from_ads), NULLIF(SUM(ad_spend), 0)), 2) AS roas
FROM `{G}.funnel_metrics`
WHERE seller_id = @seller_id
  AND metric_date >= DATE_SUB(CURRENT_DATE(), INTERVAL @days DAY)
GROUP BY sku, marketplace
ORDER BY roas DESC
"""


# ── Full Funnel (single row, overall) ──────────────────────────

FUNNEL_OVERALL_SQL = f"""
SELECT
  metric_date,
  SUM(impressions)       AS impressions,
  SUM(product_views)     AS product_views,
  SUM(add_to_cart)       AS add_to_cart,
  SUM(checkout_starts)   AS checkout_starts,
  SUM(purchases)         AS purchases,
  ROUND(AVG(overall_conversion_rate) * 100, 2) AS avg_conversion_rate_pct,
  ROUND(AVG(roas), 2)    AS avg_roas
FROM `{G}.funnel_metrics`
WHERE seller_id = @seller_id
  AND metric_date >= DATE_SUB(CURRENT_DATE(), INTERVAL @days DAY)
GROUP BY metric_date
ORDER BY metric_date
"""


# ── Logistics RTO Rate ─────────────────────────────────────────

LOGISTICS_RTO_SQL = f"""
SELECT
  marketplace,
  COUNT(*)                                                   AS total_shipments,
  COUNTIF(rto_flag)                                          AS rto_count,
  ROUND(SAFE_DIVIDE(COUNTIF(rto_flag), COUNT(*)) * 100, 2)   AS rto_rate_pct,
  COUNTIF(delivery_status = 'delivered')                     AS delivered,
  ROUND(AVG(CAST(shipping_time_days AS FLOAT64)), 1)         AS avg_shipping_days,
  fulfillment_type
FROM `{B}.logistics_metrics`
WHERE seller_id = @seller_id
  AND snapshot_date >= DATE_SUB(CURRENT_DATE(), INTERVAL @days DAY)
GROUP BY marketplace, fulfillment_type
ORDER BY rto_rate_pct DESC
"""
