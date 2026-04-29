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
S = settings.BQ_DATASET_SILVER
R = settings.BQ_DATASET_RAW


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
FROM `{S}.inventory_snapshots`
WHERE seller_id = @seller_id
  AND snapshot_date = (
    SELECT MAX(snapshot_date) FROM `{S}.inventory_snapshots`
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
FROM `{B}.logistics`
WHERE seller_id = @seller_id
  AND snapshot_date >= DATE_SUB(CURRENT_DATE(), INTERVAL @days DAY)
GROUP BY marketplace, fulfillment_type
ORDER BY rto_rate_pct DESC
"""


# ── Storefront Events: Overview ─────────────────────────────────

STOREFRONT_OVERVIEW_SQL = f"""
SELECT
  COUNTIF(event_type = 'page_view')     AS total_visits,
  COUNT(DISTINCT session_id)            AS unique_sessions,
  COUNTIF(event_type = 'product_view')  AS product_views,
  COUNTIF(event_type = 'add_to_cart')   AS cart_adds,
  COUNTIF(event_type = 'purchase')      AS orders,
  ROUND(SUM(IF(event_type = 'purchase', price * quantity, 0)), 2) AS total_revenue,
  ROUND(
    SAFE_DIVIDE(
      COUNTIF(event_type = 'purchase'),
      NULLIF(COUNT(DISTINCT session_id), 0)
    ) * 100, 2
  ) AS conversion_rate_pct
FROM `{R}.storefront_events`
WHERE seller_id = @seller_id
  AND ts >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL @days DAY)
"""


# ── Storefront Events: Daily Traffic ───────────────────────────

STOREFRONT_DAILY_TRAFFIC_SQL = f"""
SELECT
  DATE(ts)                             AS visit_date,
  COUNTIF(event_type = 'page_view')    AS visits,
  COUNT(DISTINCT session_id)           AS unique_sessions
FROM `{R}.storefront_events`
WHERE seller_id = @seller_id
  AND ts >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL @days DAY)
GROUP BY visit_date
ORDER BY visit_date
"""


# ── Storefront Events: Hourly Traffic (last N hours) ───────────

STOREFRONT_HOURLY_TRAFFIC_SQL = f"""
SELECT
  FORMAT_TIMESTAMP('%H:00', ts, 'Asia/Kolkata') AS hour_label,
  COUNTIF(event_type = 'page_view')             AS visits,
  COUNT(DISTINCT session_id)                    AS unique_sessions
FROM `{R}.storefront_events`
WHERE seller_id = @seller_id
  AND ts >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL @hours HOUR)
GROUP BY hour_label
ORDER BY hour_label
"""


# ── Storefront Events: Per-Product Performance ─────────────────

STOREFRONT_PRODUCTS_SQL = f"""
SELECT
  product_id,
  product_name,
  COUNTIF(event_type = 'product_view') AS views,
  COUNTIF(event_type = 'add_to_cart')  AS cart_adds,
  COUNTIF(event_type = 'purchase')     AS purchases,
  ROUND(SUM(IF(event_type = 'purchase', price * quantity, 0)), 2) AS revenue,
  ROUND(
    SAFE_DIVIDE(
      COUNTIF(event_type = 'purchase'),
      NULLIF(COUNTIF(event_type = 'product_view'), 0)
    ) * 100, 2
  ) AS conversion_pct
FROM `{R}.storefront_events`
WHERE seller_id = @seller_id
  AND product_id != ''
  AND ts >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL @days DAY)
GROUP BY product_id, product_name
ORDER BY revenue DESC
"""


# ── Storefront Events: Funnel ──────────────────────────────────

STOREFRONT_FUNNEL_SQL = f"""
SELECT
  COUNTIF(event_type = 'page_view')    AS page_views,
  COUNTIF(event_type = 'product_view') AS product_views,
  COUNTIF(event_type = 'add_to_cart')  AS cart_adds,
  COUNTIF(event_type = 'purchase')     AS purchases
FROM `{R}.storefront_events`
WHERE seller_id = @seller_id
  AND ts >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL @days DAY)
"""


# ── Product Catalog: Current Stock ─────────────────────────────

PRODUCT_STOCK_SQL = f"""
SELECT
  c.product_id,
  c.product_name,
  c.category,
  c.price,
  c.initial_stock,
  COALESCE(SUM(e.quantity), 0)                                            AS units_sold,
  GREATEST(c.initial_stock - COALESCE(SUM(e.quantity), 0), 0)            AS current_stock
FROM `{R}.product_catalog` c
LEFT JOIN `{R}.storefront_events` e
  ON  e.product_id  = c.product_id
  AND e.event_type  = 'purchase'
  AND e.seller_id   = @seller_id
WHERE c.seller_id = @seller_id
GROUP BY c.product_id, c.product_name, c.category, c.price, c.initial_stock
ORDER BY current_stock ASC
"""


# ── Product Catalog (storefront) ──────────────────────────────

PRODUCTS_SQL = f"""
SELECT
  product_id,
  product_name                                                             AS name,
  category,
  CAST(price AS FLOAT64)                                                   AS price,
  COALESCE(description, '')                                                AS description,
  COALESCE(
    image_path,
    CONCAT('/products/', LOWER(product_id), '.jpg')
  )                                                                        AS image,
  COALESCE(CAST(rating AS FLOAT64), 4.0)                                   AS rating,
  COALESCE(CAST(reviews AS INT64), 0)                                      AS reviews,
  COALESCE(badge, '')                                                      AS badge
FROM `{R}.product_catalog`
WHERE seller_id = @seller_id
ORDER BY product_id
"""


# ── Restock: DML UPDATE on product_catalog ─────────────────────

RESTOCK_SQL = f"""
UPDATE `{R}.product_catalog`
SET initial_stock = initial_stock + @quantity
WHERE product_id = @product_id
  AND seller_id  = @seller_id
"""


# ── Product Recommendations ────────────────────────────────────

RECOMMENDATIONS_SQL = f"""
WITH demand AS (
  SELECT
    product_id,
    COUNTIF(event_type = 'product_view')               AS views,
    COUNTIF(event_type = 'add_to_cart')                AS cart_adds,
    COUNTIF(event_type = 'purchase')                   AS purchase_events,
    SUM(IF(event_type = 'purchase', quantity, 0))      AS units_sold_period
  FROM `{R}.storefront_events`
  WHERE seller_id = @seller_id
    AND ts >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL @days DAY)
  GROUP BY product_id
),
stock AS (
  SELECT
    c.product_id, c.product_name, c.category, c.price, c.initial_stock,
    GREATEST(c.initial_stock - COALESCE(SUM(e.quantity), 0), 0) AS current_stock
  FROM `{R}.product_catalog` c
  LEFT JOIN `{R}.storefront_events` e
    ON  e.product_id = c.product_id
    AND e.event_type = 'purchase'
    AND e.seller_id  = @seller_id
  WHERE c.seller_id = @seller_id
  GROUP BY c.product_id, c.product_name, c.category, c.price, c.initial_stock
)
SELECT
  s.product_id,
  s.product_name,
  s.category,
  s.price,
  s.initial_stock,
  s.current_stock,
  COALESCE(d.views, 0)                                             AS views,
  COALESCE(d.cart_adds, 0)                                         AS cart_adds,
  COALESCE(d.purchase_events, 0)                                   AS purchases,
  ROUND(
    COALESCE(d.views, 0) * 0.2
    + COALESCE(d.cart_adds, 0) * 0.5
    + COALESCE(d.purchase_events, 0) * 1.0, 2
  )                                                                AS demand_score,
  ROUND(
    SAFE_DIVIDE(COALESCE(d.purchase_events, 0),
                NULLIF(COALESCE(d.views, 0), 0)) * 100, 1
  )                                                                AS conversion_pct,
  ROUND(s.price * s.current_stock, 0)                              AS revenue_at_risk,
  ROUND(s.price * COALESCE(d.purchase_events, 0), 0)              AS revenue_generated,
  CASE
    WHEN s.current_stock <= 2
      AND (COALESCE(d.views,0)*0.2 + COALESCE(d.cart_adds,0)*0.5
           + COALESCE(d.purchase_events,0)*1.0) >= 1
      THEN 'RESTOCK_URGENT'
    WHEN s.current_stock <= 4
      AND (COALESCE(d.views,0)*0.2 + COALESCE(d.cart_adds,0)*0.5
           + COALESCE(d.purchase_events,0)*1.0) >= 0.5
      THEN 'RESTOCK_SOON'
    WHEN COALESCE(d.views, 0) >= 5
      AND SAFE_DIVIDE(COALESCE(d.purchase_events,0),
                      NULLIF(COALESCE(d.views,0),0)) >= 0.20
      THEN 'INCREASE_PRICE'
    WHEN COALESCE(d.views, 0) >= 4
      AND SAFE_DIVIDE(COALESCE(d.purchase_events,0),
                      NULLIF(COALESCE(d.views,0),0)) < 0.05
      THEN 'DISCOUNT'
    WHEN COALESCE(d.views, 0) < 2
      AND COALESCE(d.purchase_events, 0) = 0
      THEN 'DONT_RESTOCK'
    ELSE 'MAINTAIN'
  END                                                              AS recommendation
FROM stock s
LEFT JOIN demand d USING (product_id)
ORDER BY demand_score DESC
"""
