-- cp_bronze.logistics
-- Cleaned, deduplicated logistics records from raw uploads.

{{
  config(
    materialized = 'incremental',
    partition_by = { 'field': 'snapshot_date', 'data_type': 'date' },
    cluster_by   = ['seller_id', 'marketplace'],
    unique_key   = ['seller_id', 'external_order_id', 'marketplace'],
    incremental_strategy = 'merge'
  )
}}

WITH cleaned AS (
  SELECT
    seller_id,
    external_order_id,
    marketplace,
    courier_name,
    tracking_id,
    fulfillment_type,
    warehouse_id,
    CAST(dispatch_date AS DATE)                      AS dispatch_date,
    CAST(expected_delivery AS DATE)                  AS expected_delivery,
    CAST(actual_delivery AS DATE)                    AS actual_delivery,
    shipping_time_days,
    delivery_status,
    COALESCE(rto_flag, FALSE)                        AS rto_flag,
    rto_reason,
    CAST(snapshot_date AS DATE)                      AS snapshot_date,
    ingest_timestamp,
    ROW_NUMBER() OVER (
      PARTITION BY seller_id, COALESCE(external_order_id, tracking_id), marketplace
      ORDER BY ingest_timestamp DESC
    ) AS rn
  FROM {{ source('cp_raw_ingestion', 'logistics') }}
  WHERE marketplace IS NOT NULL
    AND delivery_status IS NOT NULL
    {% if is_incremental() %}
      AND ingest_timestamp > (SELECT MAX(ingest_timestamp) FROM {{ this }})
    {% endif %}
)

SELECT * EXCEPT (rn)
FROM cleaned
WHERE rn = 1
