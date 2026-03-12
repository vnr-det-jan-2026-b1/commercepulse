"""
CommercePulse++ Batch Ingestion Pipeline
GCS (Excel/CSV) → BigQuery bronze tables via Cloud Dataflow (Apache Beam)

Usage:
    python ingestion_pipeline.py \
        --project=commercepulse-prod \
        --region=asia-south1 \
        --gcs_uri=gs://commercepulse-raw-uploads/seller-001/orders/2026-03-12/orders.xlsx \
        --domain=orders \
        --seller_id=seller-001 \
        --snapshot_date=2026-03-12 \
        --runner=DataflowRunner \
        --temp_location=gs://commercepulse-dataflow-staging-prod/temp \
        --staging_location=gs://commercepulse-dataflow-staging-prod/staging
"""
import argparse
import logging
from datetime import date

import apache_beam as beam
from apache_beam.options.pipeline_options import PipelineOptions, GoogleCloudOptions, StandardOptions
from apache_beam.io.gcp.bigquery import WriteToBigQuery, BigQueryDisposition

from transforms.parsers import ParseExcelDoFn

logger = logging.getLogger(__name__)

# ── BigQuery table IDs per domain ──────────────────────────────
BQ_TABLES = {
    "orders":     "cp_bronze.orders",
    "inventory":  "cp_bronze.inventory_snapshots",
    "pricing":    "cp_bronze.pricing_snapshots",
    "traffic":    "cp_bronze.traffic_metrics",
    "logistics":  "cp_bronze.logistics_metrics",
}

# ── BigQuery schemas per domain ────────────────────────────────
BQ_SCHEMAS = {
    "orders": {
        "fields": [
            {"name": "seller_id",            "type": "STRING",  "mode": "REQUIRED"},
            {"name": "external_order_id",    "type": "STRING",  "mode": "NULLABLE"},
            {"name": "sku",                  "type": "STRING",  "mode": "REQUIRED"},
            {"name": "marketplace",          "type": "STRING",  "mode": "REQUIRED"},
            {"name": "order_status",         "type": "STRING",  "mode": "REQUIRED"},
            {"name": "quantity",             "type": "INTEGER", "mode": "NULLABLE"},
            {"name": "selling_price",        "type": "FLOAT",   "mode": "NULLABLE"},
            {"name": "cost_price",           "type": "FLOAT",   "mode": "NULLABLE"},
            {"name": "discount",             "type": "FLOAT",   "mode": "NULLABLE"},
            {"name": "tax",                  "type": "FLOAT",   "mode": "NULLABLE"},
            {"name": "shipping_fee",         "type": "FLOAT",   "mode": "NULLABLE"},
            {"name": "net_revenue",          "type": "FLOAT",   "mode": "NULLABLE"},
            {"name": "order_date",           "type": "DATE",    "mode": "REQUIRED"},
            {"name": "delivery_date",        "type": "DATE",    "mode": "NULLABLE"},
            {"name": "return_flag",          "type": "BOOLEAN", "mode": "NULLABLE"},
            {"name": "cancellation_reason",  "type": "STRING",  "mode": "NULLABLE"},
            {"name": "ingest_timestamp",     "type": "TIMESTAMP","mode": "NULLABLE"},
        ]
    },
    "inventory": {
        "fields": [
            {"name": "seller_id",            "type": "STRING",  "mode": "REQUIRED"},
            {"name": "sku",                  "type": "STRING",  "mode": "REQUIRED"},
            {"name": "marketplace",          "type": "STRING",  "mode": "REQUIRED"},
            {"name": "available_stock",      "type": "INTEGER", "mode": "NULLABLE"},
            {"name": "reserved_stock",       "type": "INTEGER", "mode": "NULLABLE"},
            {"name": "reorder_threshold",    "type": "INTEGER", "mode": "NULLABLE"},
            {"name": "days_of_stock",        "type": "FLOAT",   "mode": "NULLABLE"},
            {"name": "warehouse_location",   "type": "STRING",  "mode": "NULLABLE"},
            {"name": "snapshot_date",        "type": "DATE",    "mode": "REQUIRED"},
            {"name": "ingest_timestamp",     "type": "TIMESTAMP","mode": "NULLABLE"},
        ]
    },
    "pricing": {
        "fields": [
            {"name": "seller_id",            "type": "STRING",  "mode": "REQUIRED"},
            {"name": "sku",                  "type": "STRING",  "mode": "REQUIRED"},
            {"name": "marketplace",          "type": "STRING",  "mode": "REQUIRED"},
            {"name": "selling_price",        "type": "FLOAT",   "mode": "NULLABLE"},
            {"name": "cost_price",           "type": "FLOAT",   "mode": "NULLABLE"},
            {"name": "mrp",                  "type": "FLOAT",   "mode": "NULLABLE"},
            {"name": "commission_pct",       "type": "FLOAT",   "mode": "NULLABLE"},
            {"name": "commission_amount",    "type": "FLOAT",   "mode": "NULLABLE"},
            {"name": "discount_percentage",  "type": "FLOAT",   "mode": "NULLABLE"},
            {"name": "net_margin",           "type": "FLOAT",   "mode": "NULLABLE"},
            {"name": "margin_pct",           "type": "FLOAT",   "mode": "NULLABLE"},
            {"name": "snapshot_date",        "type": "DATE",    "mode": "REQUIRED"},
            {"name": "ingest_timestamp",     "type": "TIMESTAMP","mode": "NULLABLE"},
        ]
    },
    "traffic": {
        "fields": [
            {"name": "seller_id",            "type": "STRING",  "mode": "REQUIRED"},
            {"name": "sku",                  "type": "STRING",  "mode": "REQUIRED"},
            {"name": "marketplace",          "type": "STRING",  "mode": "REQUIRED"},
            {"name": "metric_date",          "type": "DATE",    "mode": "REQUIRED"},
            {"name": "impressions",          "type": "INTEGER", "mode": "NULLABLE"},
            {"name": "clicks",               "type": "INTEGER", "mode": "NULLABLE"},
            {"name": "add_to_cart",          "type": "INTEGER", "mode": "NULLABLE"},
            {"name": "orders",               "type": "INTEGER", "mode": "NULLABLE"},
            {"name": "ad_spend",             "type": "FLOAT",   "mode": "NULLABLE"},
            {"name": "revenue_from_ads",     "type": "FLOAT",   "mode": "NULLABLE"},
            {"name": "ingest_timestamp",     "type": "TIMESTAMP","mode": "NULLABLE"},
        ]
    },
    "logistics": {
        "fields": [
            {"name": "seller_id",            "type": "STRING",  "mode": "REQUIRED"},
            {"name": "external_order_id",    "type": "STRING",  "mode": "NULLABLE"},
            {"name": "marketplace",          "type": "STRING",  "mode": "REQUIRED"},
            {"name": "courier_name",         "type": "STRING",  "mode": "NULLABLE"},
            {"name": "tracking_id",          "type": "STRING",  "mode": "NULLABLE"},
            {"name": "fulfillment_type",     "type": "STRING",  "mode": "NULLABLE"},
            {"name": "warehouse_id",         "type": "STRING",  "mode": "NULLABLE"},
            {"name": "dispatch_date",        "type": "DATE",    "mode": "NULLABLE"},
            {"name": "expected_delivery",    "type": "DATE",    "mode": "NULLABLE"},
            {"name": "actual_delivery",      "type": "DATE",    "mode": "NULLABLE"},
            {"name": "shipping_time_days",   "type": "INTEGER", "mode": "NULLABLE"},
            {"name": "delivery_status",      "type": "STRING",  "mode": "REQUIRED"},
            {"name": "rto_flag",             "type": "BOOLEAN", "mode": "NULLABLE"},
            {"name": "rto_reason",           "type": "STRING",  "mode": "NULLABLE"},
            {"name": "snapshot_date",        "type": "DATE",    "mode": "REQUIRED"},
            {"name": "ingest_timestamp",     "type": "TIMESTAMP","mode": "NULLABLE"},
        ]
    },
}


def run(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--project",       required=True)
    parser.add_argument("--gcs_uri",       required=True, help="gs:// path to the file")
    parser.add_argument("--domain",        required=True, choices=list(BQ_TABLES.keys()))
    parser.add_argument("--seller_id",     required=True)
    parser.add_argument("--snapshot_date", default=str(date.today()))
    known_args, pipeline_args = parser.parse_known_args(argv)

    options = PipelineOptions(pipeline_args)
    options.view_as(GoogleCloudOptions).project = known_args.project
    options.view_as(StandardOptions).runner = options.view_as(StandardOptions).runner or "DirectRunner"

    bq_table = f"{known_args.project}:{BQ_TABLES[known_args.domain]}"
    bq_schema = BQ_SCHEMAS[known_args.domain]
    dead_letter_table = f"{known_args.project}:cp_raw.ingestion_errors"

    with beam.Pipeline(options=options) as p:
        raw_bytes = (
            p
            | "ReadFromGCS" >> beam.io.ReadFromText(known_args.gcs_uri, skip_header_lines=0)
        )

        # For binary files (Excel), read directly
        file_bytes = (
            p
            | "ReadFileBytes" >> beam.Create([known_args.gcs_uri])
            | "DownloadFile" >> beam.Map(
                lambda uri: __import__("google.cloud.storage", fromlist=["Client"])
                .Client()
                .bucket(uri.split("/")[2])
                .blob("/".join(uri.split("/")[3:]))
                .download_as_bytes()
            )
        )

        parsed = (
            file_bytes
            | "ParseExcel" >> beam.ParDo(
                ParseExcelDoFn(
                    domain=known_args.domain,
                    seller_id=known_args.seller_id,
                    snapshot_date=known_args.snapshot_date,
                ),
            ).with_outputs(ParseExcelDoFn.DEAD_LETTER, main="valid")
        )

        # Write valid rows to BigQuery
        (
            parsed.valid
            | "WriteToBigQuery" >> WriteToBigQuery(
                table=bq_table,
                schema=bq_schema,
                write_disposition=BigQueryDisposition.WRITE_APPEND,
                create_disposition=BigQueryDisposition.CREATE_NEVER,
            )
        )

        # Write dead-letter rows
        (
            parsed[ParseExcelDoFn.DEAD_LETTER]
            | "FormatDeadLetter" >> beam.Map(lambda r: {
                "domain": r.get("domain", known_args.domain),
                "seller_id": known_args.seller_id,
                "error_message": r.get("error", "unknown"),
                "raw_row": str(r.get("row", {}))[:1024],
                "ingest_timestamp": __import__("datetime").datetime.utcnow().isoformat(),
            })
            | "WriteDeadLetter" >> WriteToBigQuery(
                table=dead_letter_table,
                schema={
                    "fields": [
                        {"name": "domain",           "type": "STRING",    "mode": "NULLABLE"},
                        {"name": "seller_id",        "type": "STRING",    "mode": "NULLABLE"},
                        {"name": "error_message",    "type": "STRING",    "mode": "NULLABLE"},
                        {"name": "raw_row",          "type": "STRING",    "mode": "NULLABLE"},
                        {"name": "ingest_timestamp", "type": "TIMESTAMP", "mode": "NULLABLE"},
                    ]
                },
                write_disposition=BigQueryDisposition.WRITE_APPEND,
                create_disposition=BigQueryDisposition.CREATE_IF_NEEDED,
            )
        )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run()
