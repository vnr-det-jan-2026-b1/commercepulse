-- cp_silver.traffic_metrics
-- Aggregated traffic and ad metrics per (seller, sku, marketplace, date).
-- Used by funnel_metrics and seller_dashboard_kpis.

{{
  config(
    materialized = 'incremental',
    partition_by = { 'field': 'metric_date', 'data_type': 'date' },
    cluster_by   = ['seller_id', 'sku'],
    unique_key   = ['seller_id', 'sku', 'marketplace', 'metric_date'],
    incremental_strategy = 'merge'
  )
}}

SELECT
  seller_id,
  sku,
  marketplace,
  metric_date,
  SUM(impressions)                                               AS impressions,
  SUM(clicks)                                                    AS clicks,
  SUM(add_to_cart)                                               AS add_to_cart,
  SUM(orders)                                                    AS orders,
  SUM(ad_spend)                                                  AS ad_spend,
  SUM(revenue_from_ads)                                          AS revenue_from_ads,
  SAFE_DIVIDE(SUM(clicks), NULLIF(SUM(impressions), 0))          AS ctr,
  SAFE_DIVIDE(SUM(revenue_from_ads), NULLIF(SUM(ad_spend), 0))   AS roas
FROM {{ ref('traffic') }}
{% if is_incremental() %}
  WHERE metric_date > (SELECT MAX(metric_date) - 3 FROM {{ this }})
{% endif %}
GROUP BY 1, 2, 3, 4
