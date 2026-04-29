"""
Cloud Composer DAG: ML Pipeline Orchestration
Triggers Vertex AI Pipelines on a nightly schedule.
"""
import os
from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.google.cloud.operators.vertex_ai.pipeline_job import (
    RunPipelineJobOperator,
)

PROJECT  = os.getenv("GCP_PROJECT", "commercepulse-project")
REGION   = os.getenv("GCP_REGION",  "asia-south1")
SA       = f"sa-vertex-pipelines@{PROJECT}.iam.gserviceaccount.com"
ROOT     = f"gs://commercepulse-artifacts-prod/pipelines"

DEFAULT_ARGS = {
    "owner":            "commercepulse-google-squad",
    "depends_on_past":  False,
    "email_on_failure": True,
    "email":            ["alerts@commercepulse.app"],
    "retries":          1,
    "retry_delay":      timedelta(minutes=10),
}

with DAG(
    dag_id="ml_pipeline_dag",
    default_args=DEFAULT_ARGS,
    description="Nightly Vertex AI ML pipeline runs: demand forecast + inventory risk",
    schedule_interval="0 20 * * *",   # 20:00 UTC = 01:30 IST
    start_date=datetime(2026, 1, 1),
    catchup=False,
    tags=["ml", "vertex-ai", "forecasting"],
) as dag:

    run_demand_forecast = RunPipelineJobOperator(
        task_id="run_demand_forecast_pipeline",
        project_id=PROJECT,
        region=REGION,
        display_name=f"demand-forecast-{{{{ ds }}}}",
        template_path=f"{ROOT}/demand-forecast/demand_forecast_pipeline.json",
        pipeline_root=f"{ROOT}/demand-forecast",
        service_account=SA,
        parameter_values={
            "project":        PROJECT,
            "dataset_ml":     "cp_ml",
            "dataset_bronze": "cp_bronze",
            "dataset_gold":   "cp_gold",
        },
        failure_policy="PIPELINE_FAILURE_POLICY_FAIL_SLOW",
    )

    run_demand_forecast
