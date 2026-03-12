-- cp_gold.inventory_risk_scores
-- Inventory risk classification per SKU per seller.
-- Joins latest inventory snapshot with avg daily forecast demand.

{{
  config(
    materialized = 'table',
    cluster_by   = ['seller_id', 'risk_level']
  )
}}

WITH latest_inventory AS (
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
  FROM {{ ref('inventory_snapshots') }}
  QUALIFY ROW_NUMBER() OVER (
    PARTITION BY seller_id, sku, marketplace
    ORDER BY snapshot_date DESC
  ) = 1
),

avg_daily_sales AS (
  SELECT
    seller_id,
    sku,
    marketplace,
    AVG(units_sold)    AS avg_daily_units,
    SUM(units_sold)    AS total_units_14d,
    COUNT(order_date)  AS days_with_sales
  FROM {{ ref('product_daily_sales') }}
  WHERE order_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 14 DAY)
  GROUP BY 1, 2, 3
),

forecast AS (
  -- Join with ML demand forecast if available
  SELECT
    seller_id,
    sku,
    SUM(predicted_units) AS forecast_14d_units
  FROM {{ source('cp_ml', 'demand_forecasts') }}
  WHERE forecast_date BETWEEN CURRENT_DATE() AND DATE_ADD(CURRENT_DATE(), INTERVAL 14 DAY)
  GROUP BY 1, 2
)

SELECT
  i.seller_id,
  i.sku,
  i.marketplace,
  i.available_stock,
  i.reserved_stock,
  i.reorder_threshold,
  i.snapshot_date,
  i.warehouse_location,

  COALESCE(a.avg_daily_units, 0)         AS avg_daily_units,

  -- Days of stock: use ML forecast if available, else historical avg
  CASE
    WHEN COALESCE(f.forecast_14d_units, 0) > 0
      THEN ROUND(i.available_stock / (f.forecast_14d_units / 14.0), 1)
    WHEN COALESCE(a.avg_daily_units, 0) > 0
      THEN ROUND(i.available_stock / a.avg_daily_units, 1)
    ELSE i.days_of_stock
  END                                    AS days_until_stockout,

  -- Recommended reorder quantity = 30-day demand - available
  GREATEST(0, CAST(
    COALESCE(a.avg_daily_units, 0) * 30 - i.available_stock AS INT64
  ))                                     AS recommended_reorder_qty,

  -- Risk classification
  CASE
    WHEN i.available_stock = 0 THEN 'CRITICAL'
    WHEN CASE
      WHEN COALESCE(a.avg_daily_units, 0) > 0
        THEN i.available_stock / a.avg_daily_units
      ELSE i.days_of_stock
    END <= 7  THEN 'CRITICAL'
    WHEN CASE
      WHEN COALESCE(a.avg_daily_units, 0) > 0
        THEN i.available_stock / a.avg_daily_units
      ELSE i.days_of_stock
    END <= 14 THEN 'HIGH'
    WHEN CASE
      WHEN COALESCE(a.avg_daily_units, 0) > 0
        THEN i.available_stock / a.avg_daily_units
      ELSE i.days_of_stock
    END <= 30 THEN 'MEDIUM'
    ELSE 'OK'
  END                                    AS risk_level,

  CURRENT_DATE()                         AS score_date,
  CURRENT_TIMESTAMP()                    AS computed_at

FROM latest_inventory i
LEFT JOIN avg_daily_sales a
  ON  i.seller_id   = a.seller_id
  AND i.sku         = a.sku
  AND i.marketplace = a.marketplace
LEFT JOIN forecast f
  ON  i.seller_id = f.seller_id
  AND i.sku       = f.sku
