-- cp_silver.logistics_metrics
-- Aggregated logistics performance per (seller, marketplace, date).
-- Used by seller_dashboard_kpis.

{{
  config(
    materialized = 'incremental',
    partition_by = { 'field': 'snapshot_date', 'data_type': 'date' },
    cluster_by   = ['seller_id', 'marketplace'],
    unique_key   = ['seller_id', 'marketplace', 'snapshot_date'],
    incremental_strategy = 'merge'
  )
}}

SELECT
  seller_id,
  marketplace,
  snapshot_date,
  COUNT(*)                                                        AS total_shipments,
  COUNTIF(delivery_status = 'delivered')                         AS delivered_count,
  COUNTIF(rto_flag)                                              AS rto_count,
  SAFE_DIVIDE(COUNTIF(rto_flag), COUNT(*))                       AS rto_rate,
  AVG(shipping_time_days)                                        AS avg_shipping_days,
  COUNTIF(actual_delivery > expected_delivery)                   AS late_deliveries,
  SAFE_DIVIDE(
    COUNTIF(actual_delivery > expected_delivery),
    COUNTIF(actual_delivery IS NOT NULL)
  )                                                              AS late_delivery_rate
FROM {{ ref('logistics') }}
{% if is_incremental() %}
  WHERE snapshot_date > (SELECT MAX(snapshot_date) - 1 FROM {{ this }})
{% endif %}
GROUP BY 1, 2, 3
