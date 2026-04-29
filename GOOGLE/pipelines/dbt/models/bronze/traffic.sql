-- cp_bronze.traffic
-- Cleaned traffic and ad metrics from raw uploads.

{{
  config(
    materialized = 'incremental',
    partition_by = { 'field': 'metric_date', 'data_type': 'date' },
    cluster_by   = ['seller_id', 'sku'],
    unique_key   = ['seller_id', 'sku', 'marketplace', 'metric_date'],
    incremental_strategy = 'merge'
  )
}}

WITH cleaned AS (
  SELECT
    seller_id,
    sku,
    marketplace,
    CAST(metric_date AS DATE)            AS metric_date,
    COALESCE(impressions, 0)             AS impressions,
    COALESCE(clicks, 0)                  AS clicks,
    COALESCE(add_to_cart, 0)             AS add_to_cart,
    COALESCE(orders, 0)                  AS orders,
    COALESCE(ad_spend, 0)                AS ad_spend,
    COALESCE(revenue_from_ads, 0)        AS revenue_from_ads,
    ingest_timestamp,
    ROW_NUMBER() OVER (
      PARTITION BY seller_id, sku, marketplace, metric_date
      ORDER BY ingest_timestamp DESC
    ) AS rn
  FROM {{ source('cp_raw_ingestion', 'traffic') }}
  WHERE sku IS NOT NULL
    AND marketplace IS NOT NULL
    AND metric_date IS NOT NULL
    {% if is_incremental() %}
      AND ingest_timestamp > (SELECT MAX(ingest_timestamp) FROM {{ this }})
    {% endif %}
)

SELECT * EXCEPT (rn)
FROM cleaned
WHERE rn = 1
