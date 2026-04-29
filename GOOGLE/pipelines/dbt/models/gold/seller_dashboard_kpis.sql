-- cp_gold.seller_dashboard_kpis
-- Pre-aggregated KPIs for the executive dashboard endpoint.
-- Refreshed hourly via Cloud Composer.

{{
  config(
    materialized = 'table',
    cluster_by   = ['seller_id']
  )
}}

WITH revenue_kpis AS (
  SELECT
    seller_id,
    30                                                            AS period_days,
    COALESCE(SUM(net_revenue), 0)                                 AS total_net_revenue,
    COUNT(*)                                                      AS total_orders,
    COUNTIF(order_status = 'cancelled')                           AS cancelled_orders,
    COUNTIF(return_flag)                                          AS returned_orders,
    SAFE_DIVIDE(COUNTIF(order_status = 'cancelled'), COUNT(*))    AS cancellation_rate,
    AVG(CAST(selling_price AS FLOAT64))                           AS avg_order_value
  FROM {{ ref('orders') }}
  WHERE order_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
  GROUP BY 1
),

inventory_kpis AS (
  SELECT
    seller_id,
    COUNTIF(available_stock = 0)                                  AS stockout_count,
    COUNTIF(available_stock > 0
      AND available_stock <= COALESCE(reorder_threshold, 10))     AS low_stock_count
  FROM {{ ref('inventory_snapshots') }}
  WHERE snapshot_date = (
    SELECT MAX(snapshot_date) FROM {{ ref('inventory_snapshots') }} i2
    WHERE i2.seller_id = inventory_snapshots.seller_id
  )
  GROUP BY 1
),

logistics_kpis AS (
  SELECT
    seller_id,
    SAFE_DIVIDE(SUM(rto_count), NULLIF(SUM(total_shipments), 0)) AS rto_rate
  FROM {{ ref('logistics_metrics') }}
  WHERE snapshot_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
  GROUP BY 1
),

traffic_kpis AS (
  SELECT
    seller_id,
    SAFE_DIVIDE(SUM(revenue_from_ads), NULLIF(SUM(ad_spend), 0)) AS avg_roas
  FROM {{ ref('traffic_metrics') }}
  WHERE metric_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
  GROUP BY 1
)

SELECT
  r.seller_id,
  r.period_days,
  r.total_net_revenue,
  r.total_orders,
  r.cancelled_orders,
  r.returned_orders,
  ROUND(r.cancellation_rate * 100, 2)   AS cancellation_rate_pct,
  ROUND(r.avg_order_value, 2)           AS avg_order_value,
  COALESCE(i.stockout_count, 0)         AS stockout_count,
  COALESCE(i.low_stock_count, 0)        AS low_stock_count,
  ROUND(COALESCE(l.rto_rate * 100, 0), 2) AS rto_rate_pct,
  ROUND(COALESCE(t.avg_roas, 0), 2)    AS avg_roas,
  CURRENT_TIMESTAMP()                   AS computed_at
FROM revenue_kpis r
LEFT JOIN inventory_kpis i USING (seller_id)
LEFT JOIN logistics_kpis  l USING (seller_id)
LEFT JOIN traffic_kpis    t USING (seller_id)
