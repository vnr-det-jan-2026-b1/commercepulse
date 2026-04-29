"""
CommercePulse++ Demand Forecast Pipeline
Vertex AI Kubeflow Pipeline that:
  1. Trains a BQML ARIMA_PLUS model on historical daily sales per SKU
  2. Generates 14-day forward forecasts
  3. Joins with inventory to compute days_until_stockout
  4. Writes results to cp_gold.demand_forecasts and cp_gold.inventory_risk_scores

Schedule: nightly at 02:00 IST via Cloud Composer DAG.
"""
import os
from datetime import datetime

from google.cloud import bigquery
from kfp import dsl
from kfp.v2 import compiler
from google.cloud import aiplatform

PROJECT  = os.getenv("GCP_PROJECT", "commercepulse-project")
LOCATION = os.getenv("GCP_REGION",  "asia-south1")
PIPELINE_ROOT = f"gs://commercepulse-artifacts-prod/pipelines/demand-forecast"

BQ_DATASET_BRONZE = "cp_bronze"
BQ_DATASET_GOLD   = "cp_gold"
BQ_DATASET_ML     = "cp_ml"


# ── Pipeline Components ────────────────────────────────────────

@dsl.component(
    base_image="python:3.11-slim",
    packages_to_install=["google-cloud-bigquery"],
)
def train_arima_model(project: str, dataset_ml: str, dataset_bronze: str) -> str:
    """Train BQML ARIMA_PLUS demand forecast model."""
    from google.cloud import bigquery
    client = bigquery.Client(project=project)

    sql = f"""
    CREATE OR REPLACE MODEL `{project}.{dataset_ml}.demand_forecast_arima`
    OPTIONS (
      model_type              = 'ARIMA_PLUS',
      time_series_timestamp_col = 'order_date',
      time_series_data_col    = 'units_sold',
      time_series_id_col      = ['seller_id', 'sku', 'marketplace'],
      horizon                 = 14,
      auto_arima              = TRUE,
      data_frequency          = 'DAILY',
      decompose_time_series   = TRUE,
      holiday_region          = 'IN'
    ) AS
    SELECT
      seller_id,
      sku,
      marketplace,
      order_date,
      CAST(SUM(quantity) AS FLOAT64) AS units_sold
    FROM `{project}.{dataset_bronze}.orders`
    WHERE order_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 180 DAY)
      AND order_status NOT IN ('cancelled', 'returned')
      AND sku IS NOT NULL
    GROUP BY seller_id, sku, marketplace, order_date
    HAVING units_sold > 0
    """

    job = client.query(sql)
    job.result()
    return f"{project}.{dataset_ml}.demand_forecast_arima"


@dsl.component(
    base_image="python:3.11-slim",
    packages_to_install=["google-cloud-bigquery"],
)
def generate_forecasts(project: str, model_path: str, dataset_ml: str) -> str:
    """Run ML.FORECAST and store predictions."""
    from google.cloud import bigquery
    client = bigquery.Client(project=project)

    sql = f"""
    CREATE OR REPLACE TABLE `{project}.{dataset_ml}.demand_forecasts`
    PARTITION BY forecast_date
    CLUSTER BY seller_id, sku
    AS
    SELECT
      f.time_series_timestamp         AS forecast_date,
      t.seller_id,
      t.sku,
      t.marketplace,
      ROUND(f.forecast_value, 1)      AS predicted_units,
      ROUND(f.prediction_interval_lower_bound, 1) AS prediction_interval_lower,
      ROUND(f.prediction_interval_upper_bound, 1) AS prediction_interval_upper,
      CURRENT_TIMESTAMP()             AS created_at,
      '1.0'                           AS model_version
    FROM ML.FORECAST(
      MODEL `{model_path}`,
      STRUCT(14 AS horizon, 0.9 AS confidence_level)
    ) f
    -- recover (seller_id, sku, marketplace) from the id struct
    CROSS JOIN UNNEST([STRUCT(
      SPLIT(time_series_identifier_col, '|')[OFFSET(0)] AS seller_id,
      SPLIT(time_series_identifier_col, '|')[OFFSET(1)] AS sku,
      SPLIT(time_series_identifier_col, '|')[OFFSET(2)] AS marketplace
    )]) t
    WHERE f.forecast_value >= 0
    """

    job = client.query(sql)
    job.result()
    return f"{project}.{dataset_ml}.demand_forecasts"


@dsl.component(
    base_image="python:3.11-slim",
    packages_to_install=["google-cloud-bigquery"],
)
def compute_inventory_risk(
    project:        str,
    dataset_ml:     str,
    dataset_bronze: str,
    dataset_gold:   str,
) -> int:
    """
    Join demand forecasts with latest inventory to compute
    days_until_stockout and risk classification.
    """
    from google.cloud import bigquery
    client = bigquery.Client(project=project)

    sql = f"""
    CREATE OR REPLACE TABLE `{project}.{dataset_gold}.inventory_risk_scores`
    CLUSTER BY seller_id, risk_level
    AS
    WITH latest_inv AS (
      SELECT
        seller_id, sku, marketplace,
        available_stock,
        reserved_stock,
        COALESCE(reorder_threshold, 10) AS reorder_threshold,
        snapshot_date
      FROM `{project}.{dataset_bronze}.inventory_snapshots`
      QUALIFY ROW_NUMBER() OVER (
        PARTITION BY seller_id, sku, marketplace ORDER BY snapshot_date DESC
      ) = 1
    ),
    forecast_14d AS (
      SELECT
        seller_id, sku,
        SUM(predicted_units) AS forecast_14d
      FROM `{project}.{dataset_ml}.demand_forecasts`
      WHERE forecast_date BETWEEN CURRENT_DATE()
            AND DATE_ADD(CURRENT_DATE(), INTERVAL 14 DAY)
      GROUP BY seller_id, sku
    )
    SELECT
      i.seller_id,
      i.sku,
      i.marketplace,
      i.available_stock,
      i.reserved_stock,
      i.reorder_threshold,
      i.snapshot_date,
      ROUND(COALESCE(f.forecast_14d, 0) / 14.0, 2) AS avg_daily_units,
      CASE
        WHEN COALESCE(f.forecast_14d, 0) > 0
          THEN ROUND(i.available_stock / (f.forecast_14d / 14.0), 1)
        ELSE NULL
      END                                            AS days_until_stockout,
      GREATEST(0, CAST(
        COALESCE(f.forecast_14d, 0) / 14.0 * 30 - i.available_stock AS INT64
      ))                                             AS recommended_reorder_qty,
      CASE
        WHEN i.available_stock = 0 THEN 'CRITICAL'
        WHEN COALESCE(f.forecast_14d, 0) > 0
             AND i.available_stock / (f.forecast_14d / 14.0) <= 7  THEN 'CRITICAL'
        WHEN COALESCE(f.forecast_14d, 0) > 0
             AND i.available_stock / (f.forecast_14d / 14.0) <= 14 THEN 'HIGH'
        WHEN COALESCE(f.forecast_14d, 0) > 0
             AND i.available_stock / (f.forecast_14d / 14.0) <= 30 THEN 'MEDIUM'
        ELSE 'OK'
      END                                            AS risk_level,
      CURRENT_DATE()                                 AS score_date,
      CURRENT_TIMESTAMP()                            AS computed_at
    FROM latest_inv i
    LEFT JOIN forecast_14d f
      ON i.seller_id = f.seller_id AND i.sku = f.sku
    """

    job = client.query(sql)
    job.result()

    # Return count of CRITICAL + HIGH SKUs as output
    count_job = client.query(f"""
      SELECT COUNT(*) AS cnt
      FROM `{project}.{dataset_gold}.inventory_risk_scores`
      WHERE risk_level IN ('CRITICAL', 'HIGH')
    """)
    row = list(count_job.result())[0]
    return int(row["cnt"])


# ── Pipeline Definition ────────────────────────────────────────

@dsl.pipeline(
    name="demand-forecast-pipeline",
    description="Nightly BQML ARIMA_PLUS demand forecast and inventory risk scoring",
    pipeline_root=PIPELINE_ROOT,
)
def demand_forecast_pipeline(
    project:        str = PROJECT,
    dataset_ml:     str = BQ_DATASET_ML,
    dataset_bronze: str = BQ_DATASET_BRONZE,
    dataset_gold:   str = BQ_DATASET_GOLD,
):
    train_task = train_arima_model(
        project=project,
        dataset_ml=dataset_ml,
        dataset_bronze=dataset_bronze,
    )

    forecast_task = generate_forecasts(
        project=project,
        model_path=train_task.output,
        dataset_ml=dataset_ml,
    ).after(train_task)

    compute_inventory_risk(
        project=project,
        dataset_ml=dataset_ml,
        dataset_bronze=dataset_bronze,
        dataset_gold=dataset_gold,
    ).after(forecast_task)


# ── Compile and optionally submit ─────────────────────────────

if __name__ == "__main__":
    compiled_path = "/tmp/demand_forecast_pipeline.json"
    compiler.Compiler().compile(
        pipeline_func=demand_forecast_pipeline,
        package_path=compiled_path,
    )
    print(f"Pipeline compiled to {compiled_path}")

    # Submit to Vertex AI
    aiplatform.init(project=PROJECT, location=LOCATION)
    job = aiplatform.PipelineJob(
        display_name=f"demand-forecast-{datetime.utcnow().strftime('%Y%m%d-%H%M')}",
        template_path=compiled_path,
        pipeline_root=PIPELINE_ROOT,
    )
    job.submit(service_account=f"sa-vertex-pipelines@{PROJECT}.iam.gserviceaccount.com")
    print("Pipeline submitted:", job.resource_name)
