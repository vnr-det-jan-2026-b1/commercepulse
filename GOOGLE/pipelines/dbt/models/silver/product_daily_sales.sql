-- cp_silver.product_daily_sales
-- Daily units sold and revenue per (seller, sku, marketplace).
-- Feeds demand forecasting model.

{{
  config(
    materialized = 'incremental',
    partition_by = { 'field': 'order_date', 'data_type': 'date' },
    cluster_by   = ['seller_id', 'sku'],
    unique_key   = ['seller_id', 'sku', 'marketplace', 'order_date'],
    incremental_strategy = 'merge'
  )
}}

SELECT
  seller_id,
  sku,
  marketplace,
  order_date,
  SUM(quantity)                        AS units_sold,
  SUM(net_revenue)                     AS daily_revenue,
  COUNT(*)                             AS order_count,
  COUNTIF(return_flag)                 AS return_count,
  COUNTIF(order_status = 'cancelled')  AS cancel_count,
  SAFE_DIVIDE(
    COUNTIF(return_flag), COUNT(*)
  )                                    AS return_rate,
  AVG(CAST(selling_price AS FLOAT64))  AS avg_selling_price
FROM {{ ref('orders') }}
WHERE order_status NOT IN ('cancelled', 'returned')
  {% if is_incremental() %}
    AND order_date > (SELECT MAX(order_date) - 3 FROM {{ this }})
  {% endif %}
GROUP BY 1, 2, 3, 4
