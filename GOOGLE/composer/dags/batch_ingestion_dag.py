"""
Cloud Composer (Airflow) DAG: Batch Ingestion Pipeline
Triggered by GCS object-finalization events via Pub/Sub.
Launches a Dataflow batch job to ingest the uploaded file into BigQuery.
"""
import json
import os
from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.google.cloud.operators.dataflow import DataflowStartFlexTemplateOperator
from airflow.providers.google.cloud.sensors.pubsub import PubSubPullSensor

PROJECT  = os.getenv("GCP_PROJECT", "commercepulse-project")
REGION   = os.getenv("GCP_REGION",  "asia-south1")
TEMPLATE = f"gs://commercepulse-dataflow-staging-prod/templates/batch-ingestion"
TRIGGER_SUBSCRIPTION = f"projects/{PROJECT}/subscriptions/commercepulse-batch-triggers-sub"

DEFAULT_ARGS = {
    "owner":            "commercepulse-google-squad",
    "depends_on_past":  False,
    "email_on_failure": True,
    "email":            ["alerts@commercepulse.app"],
    "retries":          2,
    "retry_delay":      timedelta(minutes=5),
}


def _parse_trigger_message(**context) -> dict:
    """Extract GCS URI and metadata from the Pub/Sub trigger message."""
    messages = context["ti"].xcom_pull(task_ids="wait_for_upload")
    if not messages:
        raise ValueError("No trigger message received")

    raw = messages[0]
    if isinstance(raw, dict):
        data = raw.get("data", {})
    else:
        import base64
        data = json.loads(base64.b64decode(raw).decode("utf-8"))

    # GCS object finalization event contains: bucket, name (path), contentType
    bucket  = data.get("bucket", "")
    name    = data.get("name", "")
    gcs_uri = f"gs://{bucket}/{name}"

    # Path format: {seller_id}/{domain}/{date}/{filename}
    parts = name.split("/")
    if len(parts) < 3:
        raise ValueError(f"Unexpected GCS path format: {name}")

    seller_id     = parts[0]
    domain        = parts[1]
    snapshot_date = parts[2]

    context["ti"].xcom_push(key="gcs_uri",       value=gcs_uri)
    context["ti"].xcom_push(key="seller_id",     value=seller_id)
    context["ti"].xcom_push(key="domain",        value=domain)
    context["ti"].xcom_push(key="snapshot_date", value=snapshot_date)

    return {"gcs_uri": gcs_uri, "seller_id": seller_id, "domain": domain}


with DAG(
    dag_id="batch_ingestion_dag",
    default_args=DEFAULT_ARGS,
    description="GCS upload → Dataflow batch ingestion → BigQuery bronze",
    schedule_interval=None,   # Event-triggered, not time-based
    start_date=datetime(2026, 1, 1),
    catchup=False,
    max_active_runs=10,       # Support concurrent uploads from multiple sellers
    tags=["ingestion", "batch", "dataflow"],
) as dag:

    wait_for_upload = PubSubPullSensor(
        task_id="wait_for_upload",
        project_id=PROJECT,
        subscription=TRIGGER_SUBSCRIPTION.split("/subscriptions/")[1],
        max_messages=1,
        ack_messages=True,
        poke_interval=10,
        timeout=300,
    )

    parse_message = PythonOperator(
        task_id="parse_trigger_message",
        python_callable=_parse_trigger_message,
        provide_context=True,
    )

    launch_dataflow = DataflowStartFlexTemplateOperator(
        task_id="launch_dataflow_ingestion",
        body={
            "launchParameter": {
                "containerSpecGcsPath": TEMPLATE,
                "jobName":  "batch-ingest-{{ ti.xcom_pull(task_ids='parse_trigger_message', key='domain') }}"
                            "-{{ ds_nodash }}-{{ ts_nodash }}",
                "parameters": {
                    "project":       PROJECT,
                    "gcs_uri":       "{{ ti.xcom_pull(task_ids='parse_trigger_message', key='gcs_uri') }}",
                    "domain":        "{{ ti.xcom_pull(task_ids='parse_trigger_message', key='domain') }}",
                    "seller_id":     "{{ ti.xcom_pull(task_ids='parse_trigger_message', key='seller_id') }}",
                    "snapshot_date": "{{ ti.xcom_pull(task_ids='parse_trigger_message', key='snapshot_date') }}",
                    "temp_location": f"gs://commercepulse-dataflow-staging-prod/temp",
                },
                "environment": {
                    "serviceAccountEmail": f"sa-dataflow@{PROJECT}.iam.gserviceaccount.com",
                    "subnetwork": f"regions/{REGION}/subnetworks/data-subnet",
                    "maxWorkers": 5,
                },
            }
        },
        project_id=PROJECT,
        location=REGION,
        wait_until_finished=True,
    )

    wait_for_upload >> parse_message >> launch_dataflow
