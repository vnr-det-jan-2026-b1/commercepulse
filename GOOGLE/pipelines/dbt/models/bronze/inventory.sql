-- cp_bronze.inventory
-- Cleaned, deduplicated inventory snapshots from raw uploads.

{{
  config(
    materialized = 'incremental',
    partition_by = { 'field': 'snapshot_date', 'data_type': 'date' },
    cluster_by   = ['seller_id', 'sku'],
    unique_key   = ['seller_id', 'sku', 'marketplace', 'snapshot_date'],
    incremental_strategy = 'merge'
  )
}}

WITH cleaned AS (
  SELECT
    seller_id,
    sku,
    marketplace,
    COALESCE(available_stock, 0)              AS available_stock,
    COALESCE(reserved_stock, 0)               AS reserved_stock,
    reorder_threshold,
    days_of_stock,
    warehouse_location,
    CAST(snapshot_date AS DATE)               AS snapshot_date,
    ingest_timestamp,
    ROW_NUMBER() OVER (
      PARTITION BY seller_id, sku, marketplace, snapshot_date
      ORDER BY ingest_timestamp DESC
    ) AS rn
  FROM {{ source('cp_raw_ingestion', 'inventory') }}
  WHERE sku IS NOT NULL
    AND marketplace IS NOT NULL
    {% if is_incremental() %}
      AND ingest_timestamp > (SELECT MAX(ingest_timestamp) FROM {{ this }})
    {% endif %}
)

SELECT * EXCEPT (rn)
FROM cleaned
WHERE rn = 1
