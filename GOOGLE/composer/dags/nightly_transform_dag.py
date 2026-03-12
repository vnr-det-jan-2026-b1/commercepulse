"""
Cloud Composer DAG: Nightly dbt Transformations
Runs dbt models to refresh silver and gold BigQuery tables.
Runs after the ML pipeline completes.
"""
import os
from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.sensors.external_task import ExternalTaskSensor

PROJECT = os.getenv("GCP_PROJECT", "commercepulse-prod")

DEFAULT_ARGS = {
    "owner":            "commercepulse-google-squad",
    "depends_on_past":  False,
    "email_on_failure": True,
    "email":            ["alerts@commercepulse.app"],
    "retries":          1,
    "retry_delay":      timedelta(minutes=5),
}

DBT_DIR = "/home/airflow/gcs/dags/dbt"

with DAG(
    dag_id="nightly_transform_dag",
    default_args=DEFAULT_ARGS,
    description="dbt runs to refresh silver → gold BigQuery tables",
    schedule_interval="30 21 * * *",  # 21:30 UTC = 03:00 IST
    start_date=datetime(2026, 1, 1),
    catchup=False,
    tags=["dbt", "transform", "bigquery"],
) as dag:

    dbt_run_bronze = BashOperator(
        task_id="dbt_run_bronze",
        bash_command=f"cd {DBT_DIR} && dbt run --select bronze --target prod",
        env={"DBT_PROFILES_DIR": DBT_DIR, "GCP_PROJECT": PROJECT},
    )

    dbt_run_silver = BashOperator(
        task_id="dbt_run_silver",
        bash_command=f"cd {DBT_DIR} && dbt run --select silver --target prod",
        env={"DBT_PROFILES_DIR": DBT_DIR, "GCP_PROJECT": PROJECT},
    )

    dbt_run_gold = BashOperator(
        task_id="dbt_run_gold",
        bash_command=f"cd {DBT_DIR} && dbt run --select gold --target prod",
        env={"DBT_PROFILES_DIR": DBT_DIR, "GCP_PROJECT": PROJECT},
    )

    dbt_test = BashOperator(
        task_id="dbt_test",
        bash_command=f"cd {DBT_DIR} && dbt test --target prod",
        env={"DBT_PROFILES_DIR": DBT_DIR, "GCP_PROJECT": PROJECT},
    )

    dbt_run_bronze >> dbt_run_silver >> dbt_run_gold >> dbt_test
