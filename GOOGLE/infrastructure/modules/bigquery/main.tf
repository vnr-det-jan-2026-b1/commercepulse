variable "project_id" {}
variable "region"     {}

locals {
  datasets = {
    cp_raw     = "Raw ingestion zone — append-only, 90-day TTL"
    cp_bronze  = "Deduplicated, typed, validated"
    cp_silver  = "Enriched and joined"
    cp_gold    = "Analytics-ready, materialized"
    cp_ml      = "BQML model artifacts and prediction outputs"
    cp_config  = "Reference data — sellers, products"
  }
}

resource "google_bigquery_dataset" "datasets" {
  for_each    = local.datasets

  dataset_id  = each.key
  description = each.value
  location    = var.region

  default_table_expiration_ms = each.key == "cp_raw" ? 7776000000 : null  # 90 days for raw

  labels = {
    environment = "prod"
    managed_by  = "terraform"
  }
}

# ── cp_raw.user_events (streaming insert target) ───────────────

resource "google_bigquery_table" "user_events" {
  dataset_id          = google_bigquery_dataset.datasets["cp_raw"].dataset_id
  table_id            = "user_events"
  deletion_protection = false

  time_partitioning {
    type  = "DAY"
    field = "event_date"
  }

  clustering = ["seller_id", "event_type"]

  schema = jsonencode([
    { name = "event_id",         type = "STRING",    mode = "REQUIRED" },
    { name = "seller_id",        type = "STRING",    mode = "REQUIRED" },
    { name = "session_id",       type = "STRING",    mode = "NULLABLE" },
    { name = "user_id_hash",     type = "STRING",    mode = "NULLABLE" },
    { name = "event_type",       type = "STRING",    mode = "REQUIRED" },
    { name = "product_sku",      type = "STRING",    mode = "NULLABLE" },
    { name = "marketplace",      type = "STRING",    mode = "NULLABLE" },
    { name = "event_timestamp",  type = "TIMESTAMP", mode = "REQUIRED" },
    { name = "event_date",       type = "DATE",      mode = "REQUIRED" },
    { name = "page_url",         type = "STRING",    mode = "NULLABLE" },
    { name = "referrer",         type = "STRING",    mode = "NULLABLE" },
    { name = "utm_source",       type = "STRING",    mode = "NULLABLE" },
    { name = "utm_medium",       type = "STRING",    mode = "NULLABLE" },
    { name = "utm_campaign",     type = "STRING",    mode = "NULLABLE" },
    { name = "device_type",      type = "STRING",    mode = "NULLABLE" },
    { name = "country_code",     type = "STRING",    mode = "NULLABLE" },
    { name = "ingest_timestamp", type = "TIMESTAMP", mode = "NULLABLE" },
  ])
}

# ── cp_raw.ingestion_errors (dead-letter) ─────────────────────

resource "google_bigquery_table" "ingestion_errors" {
  dataset_id          = google_bigquery_dataset.datasets["cp_raw"].dataset_id
  table_id            = "ingestion_errors"
  deletion_protection = false

  schema = jsonencode([
    { name = "domain",           type = "STRING",    mode = "NULLABLE" },
    { name = "seller_id",        type = "STRING",    mode = "NULLABLE" },
    { name = "error_message",    type = "STRING",    mode = "NULLABLE" },
    { name = "raw_row",          type = "STRING",    mode = "NULLABLE" },
    { name = "ingest_timestamp", type = "TIMESTAMP", mode = "NULLABLE" },
  ])
}

# ── cp_bronze tables (partitioned + clustered) ─────────────────

resource "google_bigquery_table" "orders" {
  dataset_id          = google_bigquery_dataset.datasets["cp_bronze"].dataset_id
  table_id            = "orders"
  deletion_protection = false

  time_partitioning {
    type  = "DAY"
    field = "order_date"
  }

  clustering              = ["seller_id", "marketplace"]
  require_partition_filter = true

  schema = jsonencode([
    { name = "seller_id",           type = "STRING",    mode = "REQUIRED" },
    { name = "external_order_id",   type = "STRING",    mode = "NULLABLE" },
    { name = "sku",                 type = "STRING",    mode = "REQUIRED" },
    { name = "marketplace",         type = "STRING",    mode = "REQUIRED" },
    { name = "order_status",        type = "STRING",    mode = "REQUIRED" },
    { name = "quantity",            type = "INTEGER",   mode = "NULLABLE" },
    { name = "selling_price",       type = "BIGNUMERIC",mode = "NULLABLE" },
    { name = "cost_price",          type = "BIGNUMERIC",mode = "NULLABLE" },
    { name = "discount",            type = "BIGNUMERIC",mode = "NULLABLE" },
    { name = "tax",                 type = "BIGNUMERIC",mode = "NULLABLE" },
    { name = "shipping_fee",        type = "BIGNUMERIC",mode = "NULLABLE" },
    { name = "net_revenue",         type = "BIGNUMERIC",mode = "NULLABLE" },
    { name = "order_date",          type = "DATE",      mode = "REQUIRED" },
    { name = "delivery_date",       type = "DATE",      mode = "NULLABLE" },
    { name = "return_flag",         type = "BOOLEAN",   mode = "NULLABLE" },
    { name = "cancellation_reason", type = "STRING",    mode = "NULLABLE" },
    { name = "ingest_timestamp",    type = "TIMESTAMP", mode = "NULLABLE" },
  ])
}
