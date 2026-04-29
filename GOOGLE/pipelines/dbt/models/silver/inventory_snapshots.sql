-- cp_silver.inventory_snapshots
-- Latest inventory state per (seller, sku, marketplace, date).
-- Used by inventory_risk_scores and seller_dashboard_kpis.

{{
  config(
    materialized = 'incremental',
    partition_by = { 'field': 'snapshot_date', 'data_type': 'date' },
    cluster_by   = ['seller_id', 'sku'],
    unique_key   = ['seller_id', 'sku', 'marketplace', 'snapshot_date'],
    incremental_strategy = 'merge'
  )
}}

SELECT
  seller_id,
  sku,
  marketplace,
  available_stock,
  reserved_stock,
  reorder_threshold,
  days_of_stock,
  warehouse_location,
  snapshot_date
FROM {{ ref('inventory') }}
{% if is_incremental() %}
  WHERE snapshot_date > (SELECT MAX(snapshot_date) - 1 FROM {{ this }})
{% endif %}
