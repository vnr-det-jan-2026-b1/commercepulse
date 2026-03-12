# CommercePulse++ — How to Test and Run Everything

This guide walks through running each component from scratch,
from local development to full GCP deployment.

---

## Prerequisites

Install these tools before starting:

| Tool | Install |
|---|---|
| Python 3.11 | https://python.org |
| Google Cloud SDK (`gcloud`) | https://cloud.google.com/sdk/docs/install |
| Terraform >= 1.6 | https://developer.hashicorp.com/terraform/install |
| Git | Already installed |

Optional (for front-end):
- Node.js 20+ for the React dashboard
- `dbt-bigquery` for running SQL transformations

---

## Part 1 — Run the FastAPI Backend Locally (No GCP needed for basic tests)

This runs the API entirely on your laptop using dev mode.
It skips Firebase auth and uses mock/empty BigQuery responses.

### Step 1.1 — Set up Python environment

```bash
cd GOOGLE/backend

python -m venv .venv

# Windows
.venv\Scripts\activate

# Mac/Linux
source .venv/bin/activate

pip install -r requirements.txt
```

### Step 1.2 — Configure environment

```bash
# Copy the example env file
cp .env.example .env

# Open .env and set:
#   CP_DEV_MODE=true        ← skips Firebase auth
#   GCP_PROJECT=your-project-id
```

### Step 1.3 — Authenticate with Google Cloud (needed to call BigQuery)

```bash
gcloud auth application-default login
gcloud config set project YOUR_PROJECT_ID
```

### Step 1.4 — Start the server

```bash
CP_DEV_MODE=true uvicorn app.main:app --reload --port 8000
```

You should see:
```
INFO:     Uvicorn running on http://127.0.0.1:8000
INFO:     CommercePulse++ API starting up | project=...
```

### Step 1.5 — Open the interactive API docs

Open in your browser:
```
http://localhost:8000/docs
```

This shows all endpoints. You can call them directly from the browser.

### Step 1.6 — Test endpoints with curl

```bash
SELLER="test-seller-001"

# Health check
curl http://localhost:8000/health

# Dashboard KPIs
curl "http://localhost:8000/v1/analytics/dashboard?seller_id=$SELLER" \
  -H "X-Seller-Id: $SELLER"

# Revenue summary
curl "http://localhost:8000/v1/analytics/revenue?seller_id=$SELLER&days=30" \
  -H "X-Seller-Id: $SELLER"

# Inventory alerts
curl "http://localhost:8000/v1/analytics/inventory/alerts?seller_id=$SELLER" \
  -H "X-Seller-Id: $SELLER"

# Funnel metrics
curl "http://localhost:8000/v1/analytics/funnel?seller_id=$SELLER&days=7" \
  -H "X-Seller-Id: $SELLER"

# Inventory risk scores (from ML layer)
curl "http://localhost:8000/v1/intelligence/inventory-risk?seller_id=$SELLER" \
  -H "X-Seller-Id: $SELLER"
```

> Note: These return empty arrays until you load data into BigQuery (Part 3).

### Step 1.7 — Run automated API tests

```bash
# In a separate terminal (keep the server running)
pip install pytest httpx

pytest GOOGLE/tests/test_api.py -v
```

---

## Part 2 — Test the Batch Pipeline Locally (No GCP needed)

The batch pipeline runs with Apache Beam's `DirectRunner` on your laptop —
no Dataflow or GCP connection required.

### Step 2.1 — Set up the pipeline environment

```bash
cd GOOGLE/pipelines/batch

python -m venv .venv
source .venv/bin/activate   # or .venv\Scripts\activate on Windows

pip install -r requirements.txt
```

### Step 2.2 — Generate sample Excel files

```bash
cd GOOGLE

python tests/generate_sample_data.py --output_dir sample_data
```

Output:
```
  Created sample_data/orders.xlsx    (200 rows)
  Created sample_data/inventory.xlsx (45 rows)
  Created sample_data/pricing.xlsx   (42 rows)
  Created sample_data/traffic.xlsx   (560 rows)
  Created sample_data/logistics.xlsx (150 rows)

Seller ID: test-seller-001
```

### Step 2.3 — Run pipeline unit tests

```bash
cd GOOGLE/pipelines/batch

pytest ../../tests/test_pipeline.py -v
```

Expected output:
```
PASSED tests/test_pipeline.py::test_order_col_map_normalises_selling_price
PASSED tests/test_pipeline.py::test_inventory_col_map_stock_aliases
PASSED tests/test_pipeline.py::test_parse_date_iso_string
PASSED tests/test_pipeline.py::test_safe_float
PASSED tests/test_pipeline.py::test_coerce_order_row_computes_net_revenue
PASSED tests/test_pipeline.py::test_coerce_pricing_row_computes_margin
PASSED tests/test_pipeline.py::test_parse_excel_dofn_valid_orders
PASSED tests/test_pipeline.py::test_parse_excel_dofn_missing_sku_goes_to_dead_letter
```

### Step 2.4 — Run the batch pipeline against real BigQuery

Replace `your-project` with your actual GCP project ID.
This writes directly into your BigQuery `cp_bronze` tables.

```bash
cd GOOGLE/pipelines/batch

python ingestion_pipeline.py \
  --project=your-project \
  --gcs_uri=gs://your-raw-uploads-bucket/test-seller-001/orders/2026-03-12/orders.xlsx \
  --domain=orders \
  --seller_id=test-seller-001 \
  --snapshot_date=2026-03-12 \
  --runner=DirectRunner
```

To run all 5 domains at once:

```bash
for DOMAIN in orders inventory pricing traffic logistics; do
  python ingestion_pipeline.py \
    --project=your-project \
    --gcs_uri=gs://your-raw-uploads-bucket/test-seller-001/${DOMAIN}/2026-03-12/${DOMAIN}.xlsx \
    --domain=$DOMAIN \
    --seller_id=test-seller-001 \
    --snapshot_date=2026-03-12 \
    --runner=DirectRunner
done
```

---

## Part 3 — Load Sample Data into BigQuery Directly

If you want data in BigQuery without running Dataflow, upload the Excel files
directly through the API upload endpoints or use `bq load`.

### Option A — Upload via API (recommended)

```bash
# Start the server (Part 1 Step 1.4) then run:
SELLER="test-seller-001"

for DOMAIN in orders inventory pricing traffic logistics; do
  curl -X POST "http://localhost:8000/v1/upload/${DOMAIN}" \
    -H "X-Seller-Id: $SELLER" \
    -F "seller_id=$SELLER" \
    -F "snapshot_date=2026-03-12" \
    -F "file=@GOOGLE/sample_data/${DOMAIN}.xlsx;type=application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
  echo ""
done
```

### Option B — Direct BigQuery load using Python

```python
# Run from anywhere with BigQuery credentials set up
from google.cloud import bigquery
import pandas as pd

client    = bigquery.Client(project="your-project")
seller_id = "test-seller-001"
date_str  = "2026-03-12"

df = pd.read_excel("GOOGLE/sample_data/orders.xlsx")
# Normalise columns (same as pipeline)
import sys; sys.path.insert(0, "GOOGLE/pipelines/batch")
from col_maps import ORDER_COL_MAP
df.columns = [c.strip().lower() for c in df.columns]
df = df.rename(columns={k: v for k, v in ORDER_COL_MAP.items() if k in df.columns})
df["seller_id"] = seller_id
df["ingest_timestamp"] = pd.Timestamp.utcnow()

job = client.load_table_from_dataframe(
    df,
    "your-project.cp_bronze.orders",
    job_config=bigquery.LoadJobConfig(write_disposition="WRITE_APPEND"),
)
job.result()
print(f"Loaded {job.output_rows} rows")
```

---

## Part 4 — Run dbt SQL Transformations

After data is in BigQuery bronze tables, run dbt to populate silver and gold layers.

### Step 4.1 — Install dbt

```bash
pip install dbt-bigquery
```

### Step 4.2 — Configure profiles.yml

Create `GOOGLE/pipelines/dbt/profiles.yml`:

```yaml
commercepulse_bq:
  target: dev
  outputs:
    dev:
      type: bigquery
      method: oauth
      project: your-project
      dataset: cp_bronze   # default dataset (overridden per model)
      location: asia-south1
      threads: 4
      timeout_seconds: 300
    prod:
      type: bigquery
      method: service-account
      project: your-project
      keyfile: /path/to/sa-key.json
      dataset: cp_bronze
      location: asia-south1
      threads: 8
      timeout_seconds: 600
```

### Step 4.3 — Run dbt

```bash
cd GOOGLE/pipelines/dbt

# Test connection
dbt debug

# Run bronze models (deduplication)
dbt run --select bronze

# Run silver models (enrichment)
dbt run --select silver

# Run gold models (analytics-ready)
dbt run --select gold

# Run all at once
dbt run

# Run tests
dbt test

# Run everything
dbt build
```

After this runs, your gold tables will have data and the API will return real results.

---

## Part 5 — Test the Event Collector (Streaming Lane)

### Step 5.1 — Run the event collector locally

```bash
cd GOOGLE/event-collector

pip install -r requirements.txt

# In dev mode (skips HMAC signature verification)
CP_DEV_MODE=true GCP_PROJECT=your-project \
  uvicorn main:app --reload --port 8001
```

### Step 5.2 — Send a test event

```bash
# Single event
curl -X POST "http://localhost:8001/collect/test-seller-001" \
  -H "Content-Type: application/json" \
  -d '{
    "event_type": "product_view",
    "product_sku": "SKU-0001",
    "marketplace": "flipkart",
    "page_url": "https://seller-store.com/product/SKU-0001",
    "utm_source": "google",
    "utm_medium": "cpc",
    "device_type": "mobile"
  }'
```

Expected response:
```json
{"accepted": 1, "seller_id": "test-seller-001"}
```

### Step 5.3 — Send a batch of events

```bash
curl -X POST "http://localhost:8001/collect/batch" \
  -H "Content-Type: application/json" \
  -d '{
    "seller_id": "test-seller-001",
    "events": [
      {"event_type": "product_view",    "product_sku": "SKU-0001"},
      {"event_type": "add_to_cart",     "product_sku": "SKU-0001"},
      {"event_type": "checkout_start",  "product_sku": "SKU-0001"},
      {"event_type": "purchase",        "product_sku": "SKU-0001"}
    ]
  }'
```

Expected response:
```json
{"accepted": 4, "seller_id": "test-seller-001"}
```

> These events go to Pub/Sub. The Dataflow streaming pipeline (Part 6) then reads
> them and writes to BigQuery `cp_raw.user_events`.

---

## Part 6 — Run the Streaming Pipeline Locally

```bash
cd GOOGLE/pipelines/streaming

pip install -r requirements.txt

python event_pipeline.py \
  --project=your-project \
  --runner=DirectRunner \
  --streaming
```

This connects to the real Pub/Sub subscription and BigQuery.
Leave it running in a terminal. Events sent to the collector in Part 5
will appear in `cp_raw.user_events` within a few seconds.

---

## Part 7 — Test the ML Pipeline

### Step 7.1 — Run demand forecast via BigQuery ML directly

Open the BigQuery console (https://console.cloud.google.com/bigquery) and run:

```sql
-- 1. Train the ARIMA_PLUS model (takes 2-5 minutes)
CREATE OR REPLACE MODEL `your-project.cp_ml.demand_forecast_arima`
OPTIONS (
  model_type               = 'ARIMA_PLUS',
  time_series_timestamp_col = 'order_date',
  time_series_data_col     = 'units_sold',
  time_series_id_col       = ['seller_id', 'sku', 'marketplace'],
  horizon                  = 14,
  auto_arima               = TRUE,
  data_frequency           = 'DAILY',
  holiday_region           = 'IN'
) AS
SELECT
  seller_id,
  sku,
  marketplace,
  order_date,
  CAST(SUM(quantity) AS FLOAT64) AS units_sold
FROM `your-project.cp_bronze.orders`
WHERE order_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 60 DAY)
  AND order_status NOT IN ('cancelled', 'returned')
GROUP BY seller_id, sku, marketplace, order_date
HAVING units_sold > 0;

-- 2. Generate 14-day forecasts
SELECT * FROM ML.FORECAST(
  MODEL `your-project.cp_ml.demand_forecast_arima`,
  STRUCT(14 AS horizon, 0.9 AS confidence_level)
)
LIMIT 50;
```

### Step 7.2 — Run the full Vertex AI pipeline

```bash
cd GOOGLE/ml/pipelines

pip install google-cloud-aiplatform kfp

python demand_forecast_pipeline.py
```

This compiles the pipeline and submits it to Vertex AI.
Monitor progress at: https://console.cloud.google.com/vertex-ai/pipelines

---

## Part 8 — Test the AI / Gemini Endpoints

These require a live GCP project with Vertex AI API enabled.

```bash
SELLER="test-seller-001"

# Get AI recommendations (structured JSON brief)
curl -X POST "http://localhost:8000/v1/ai/recommendations?seller_id=$SELLER" \
  -H "X-Seller-Id: $SELLER"

# Streaming chat (returns SSE)
curl -X POST "http://localhost:8000/v1/ai/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "seller_id": "test-seller-001",
    "message": "Why did my Flipkart revenue drop last week?"
  }'

# What-if scenario
curl -X POST "http://localhost:8000/v1/ai/whatif" \
  -H "Content-Type: application/json" \
  -d '{
    "seller_id": "test-seller-001",
    "scenario": "What if I reduce the price of SKU-0001 by 10%?"
  }'
```

---

## Part 9 — Deploy to GCP (Full Production)

### Step 9.1 — Set up GCP project

```bash
# Set your project
gcloud config set project your-project

# Authenticate
gcloud auth login
gcloud auth application-default login
```

### Step 9.2 — Provision infrastructure with Terraform

```bash
cd GOOGLE/infrastructure

terraform init
terraform plan -var="project_id=your-project"
terraform apply -var="project_id=your-project"
```

This creates:
- GCS buckets (raw uploads, Dataflow staging, artifacts)
- BigQuery datasets and tables
- Pub/Sub topics and subscriptions
- IAM service accounts with correct permissions

### Step 9.3 — Build and deploy with Cloud Build

```bash
# From the repo root
gcloud builds submit \
  --config=GOOGLE/cloudbuild.yaml \
  --substitutions=SHORT_SHA=$(git rev-parse --short HEAD)
```

This builds both Docker images and deploys:
- `commercepulse-event-collector` → Cloud Run
- `commercepulse-api` → Cloud Run

### Step 9.4 — Deploy Cloud Composer DAGs

```bash
# Get your Composer environment's DAG bucket
COMPOSER_BUCKET=$(gcloud composer environments describe commercepulse-orchestrator \
  --location=asia-south1 \
  --format="get(config.dagGcsPrefix)")

# Upload DAGs
gsutil cp GOOGLE/composer/dags/*.py ${COMPOSER_BUCKET}/
```

### Step 9.5 — Upload sample data to GCS and trigger ingestion

```bash
# Upload sample files to GCS (triggers the Composer DAG automatically)
BUCKET="gs://commercepulse-raw-uploads-prod"
DATE=$(date +%Y-%m-%d)
SELLER="test-seller-001"

for DOMAIN in orders inventory pricing traffic logistics; do
  gsutil cp GOOGLE/sample_data/${DOMAIN}.xlsx \
    ${BUCKET}/${SELLER}/${DOMAIN}/${DATE}/${DOMAIN}.xlsx
  echo "Uploaded ${DOMAIN}"
done
```

The GCS upload triggers a Pub/Sub notification → Cloud Composer DAG →
Dataflow batch job → BigQuery bronze tables. Takes ~5-10 minutes.

### Step 9.6 — Verify data arrived in BigQuery

```bash
bq query --use_legacy_sql=false \
  "SELECT COUNT(*) as rows, MIN(order_date), MAX(order_date)
   FROM \`your-project.cp_bronze.orders\`
   WHERE seller_id = 'test-seller-001'"
```

### Step 9.7 — Run dbt transformations

```bash
cd GOOGLE/pipelines/dbt
dbt run --target prod
dbt test --target prod
```

### Step 9.8 — Verify the production API

```bash
# Get the Cloud Run URL
API_URL=$(gcloud run services describe commercepulse-api \
  --region=asia-south1 \
  --format="get(status.url)")

echo "API URL: $API_URL"

# Test health
curl $API_URL/health

# Test with a seller (needs a valid Firebase JWT in production)
curl "$API_URL/v1/analytics/dashboard?seller_id=test-seller-001" \
  -H "Authorization: Bearer YOUR_FIREBASE_JWT"
```

---

## Part 10 — End-to-End Test Checklist

Run through this checklist to verify the full pipeline works:

```
[ ] 1. Sample data generated:
        python GOOGLE/tests/generate_sample_data.py

[ ] 2. Pipeline unit tests pass:
        pytest GOOGLE/tests/test_pipeline.py -v

[ ] 3. Backend starts in dev mode:
        CP_DEV_MODE=true uvicorn app.main:app --reload

[ ] 4. /health returns {"status": "ok"}

[ ] 5. API tests pass:
        pytest GOOGLE/tests/test_api.py -v

[ ] 6. Sample data uploaded to GCS or directly to BigQuery

[ ] 7. dbt run completes without errors

[ ] 8. /analytics/dashboard returns non-zero revenue and orders

[ ] 9. /analytics/inventory/alerts returns alerts (if low-stock SKUs exist)

[ ] 10. Event collector running, test events accepted:
         curl -X POST localhost:8001/collect/test-seller-001 ...

[ ] 11. Streaming pipeline running, events appear in cp_raw.user_events

[ ] 12. /analytics/funnel returns funnel data after streaming events land

[ ] 13. BQML demand forecast model trained (BigQuery console)

[ ] 14. /intelligence/inventory-risk returns risk scores

[ ] 15. /ai/recommendations returns a Gemini brief (needs Vertex AI API enabled)
```

---

## Quick Reference: All Commands

```bash
# Generate sample data
python GOOGLE/tests/generate_sample_data.py

# Run pipeline tests (no GCP)
cd GOOGLE/pipelines/batch && pytest ../../tests/test_pipeline.py -v

# Start API server (dev mode)
cd GOOGLE/backend && CP_DEV_MODE=true uvicorn app.main:app --reload

# Run API tests
pytest GOOGLE/tests/test_api.py -v

# Start event collector
cd GOOGLE/event-collector && CP_DEV_MODE=true uvicorn main:app --port 8001 --reload

# Run dbt
cd GOOGLE/pipelines/dbt && dbt run && dbt test

# Deploy everything to GCP
gcloud builds submit --config=GOOGLE/cloudbuild.yaml

# Terraform provision
cd GOOGLE/infrastructure && terraform apply -var="project_id=your-project"
```

---

## Troubleshooting

| Problem | Solution |
|---|---|
| `google.auth.exceptions.DefaultCredentialsError` | Run `gcloud auth application-default login` |
| BigQuery returns empty results | Run `dbt run` first to populate gold tables |
| 403 on API calls | Set `CP_DEV_MODE=true` in `.env` for local dev |
| Pub/Sub publish fails | Check `GCP_PROJECT` env var is set correctly |
| Dataflow job fails on DirectRunner | Ensure `pandas` and `openpyxl` are installed |
| Gemini returns 403 | Enable Vertex AI API: `gcloud services enable aiplatform.googleapis.com` |
| `ModuleNotFoundError: col_maps` | Run from `GOOGLE/pipelines/batch/` directory |
