-- cp_gold.funnel_metrics
-- Daily conversion funnel metrics per (seller, sku, marketplace).
-- Combines streaming events + batch traffic data.

{{
  config(
    materialized = 'table',
    partition_by = { 'field': 'metric_date', 'data_type': 'date' },
    cluster_by   = ['seller_id', 'marketplace']
  )
}}

WITH event_funnel AS (
  -- From streaming user events
  SELECT
    seller_id,
    product_sku                           AS sku,
    marketplace,
    event_date                            AS metric_date,
    COUNTIF(event_type = 'product_view')  AS product_views,
    COUNTIF(event_type = 'add_to_cart')   AS add_to_cart,
    COUNTIF(event_type = 'checkout_start')AS checkout_starts,
    COUNTIF(event_type = 'purchase')      AS purchases,
    COUNT(DISTINCT session_id)            AS unique_sessions,
    AVG(TIMESTAMP_DIFF(
      MAX(event_timestamp) OVER (PARTITION BY session_id),
      MIN(event_timestamp) OVER (PARTITION BY session_id),
      SECOND
    ))                                    AS avg_session_duration_sec
  FROM {{ source('cp_raw', 'user_events') }}
  WHERE product_sku IS NOT NULL
  GROUP BY 1, 2, 3, 4
),

traffic_funnel AS (
  -- From batch traffic metrics (impressions, clicks from marketplace)
  SELECT
    seller_id,
    sku,
    marketplace,
    metric_date,
    SUM(impressions) AS impressions,
    SUM(clicks)      AS clicks,
    SUM(add_to_cart) AS traffic_add_to_cart,
    SUM(orders)      AS traffic_orders,
    SUM(ad_spend)    AS ad_spend,
    SUM(revenue_from_ads) AS revenue_from_ads
  FROM {{ ref('traffic_metrics') }}
  GROUP BY 1, 2, 3, 4
)

SELECT
  COALESCE(e.seller_id, t.seller_id)     AS seller_id,
  COALESCE(e.sku, t.sku)                 AS sku,
  COALESCE(e.marketplace, t.marketplace) AS marketplace,
  COALESCE(e.metric_date, t.metric_date) AS metric_date,

  -- Prefer event-based counts, fall back to traffic metrics
  COALESCE(t.impressions, 0)             AS impressions,
  COALESCE(t.clicks, 0)                  AS clicks,
  COALESCE(e.product_views, 0)           AS product_views,
  COALESCE(e.add_to_cart, t.traffic_add_to_cart, 0) AS add_to_cart,
  COALESCE(e.checkout_starts, 0)         AS checkout_starts,
  COALESCE(e.purchases, t.traffic_orders, 0) AS purchases,
  COALESCE(e.unique_sessions, 0)         AS unique_sessions,
  e.avg_session_duration_sec,

  -- Funnel rates
  SAFE_DIVIDE(e.add_to_cart, NULLIF(e.product_views, 0))    AS view_to_cart_rate,
  SAFE_DIVIDE(e.checkout_starts, NULLIF(e.add_to_cart, 0))  AS cart_to_checkout_rate,
  SAFE_DIVIDE(e.purchases, NULLIF(e.checkout_starts, 0))    AS checkout_to_purchase_rate,
  SAFE_DIVIDE(e.purchases, NULLIF(e.product_views, 0))      AS overall_conversion_rate,
  SAFE_DIVIDE(t.clicks, NULLIF(t.impressions, 0))           AS ctr,

  -- Ad performance
  COALESCE(t.ad_spend, 0)                AS ad_spend,
  COALESCE(t.revenue_from_ads, 0)        AS revenue_from_ads,
  SAFE_DIVIDE(t.revenue_from_ads, NULLIF(t.ad_spend, 0)) AS roas,

  CURRENT_TIMESTAMP()                    AS computed_at

FROM event_funnel e
FULL OUTER JOIN traffic_funnel t
  ON  e.seller_id   = t.seller_id
  AND e.sku         = t.sku
  AND e.marketplace = t.marketplace
  AND e.metric_date = t.metric_date
