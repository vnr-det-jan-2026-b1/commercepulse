-- cp_bronze.orders
-- Deduplicated, typed orders from the raw ingestion layer.
-- Partitioned by order_date, clustered by seller_id, marketplace.

{{
  config(
    materialized = 'incremental',
    partition_by = { 'field': 'order_date', 'data_type': 'date' },
    cluster_by   = ['seller_id', 'marketplace'],
    unique_key   = ['seller_id', 'external_order_id', 'sku', 'marketplace'],
    incremental_strategy = 'merge'
  )
}}

WITH deduped AS (
  SELECT
    seller_id,
    external_order_id,
    sku,
    marketplace,
    order_status,
    COALESCE(quantity, 1)                              AS quantity,
    CAST(selling_price   AS BIGNUMERIC)                AS selling_price,
    CAST(cost_price      AS BIGNUMERIC)                AS cost_price,
    CAST(discount        AS BIGNUMERIC)                AS discount,
    CAST(tax             AS BIGNUMERIC)                AS tax,
    CAST(shipping_fee    AS BIGNUMERIC)                AS shipping_fee,
    CAST(net_revenue     AS BIGNUMERIC)                AS net_revenue,
    PARSE_DATE('%Y-%m-%d', order_date)                 AS order_date,
    SAFE.PARSE_DATE('%Y-%m-%d', delivery_date)         AS delivery_date,
    COALESCE(return_flag, FALSE)                       AS return_flag,
    cancellation_reason,
    ingest_timestamp,
    ROW_NUMBER() OVER (
      PARTITION BY seller_id, COALESCE(external_order_id, GENERATE_UUID()), sku, marketplace
      ORDER BY ingest_timestamp DESC
    ) AS rn
  FROM {{ source('cp_raw_ingestion', 'orders') }}
  WHERE seller_id IS NOT NULL
    AND sku IS NOT NULL
    AND order_date IS NOT NULL
    {% if is_incremental() %}
      AND ingest_timestamp > (SELECT MAX(ingest_timestamp) FROM {{ this }})
    {% endif %}
)

SELECT * EXCEPT (rn)
FROM deduped
WHERE rn = 1
