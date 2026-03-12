# CommercePulse++ — Full Technical Blueprint

**Platform:** Google Cloud Native
**Purpose:** Analytics and intelligence platform for e-commerce sellers
**Team:** Google Squad (S Sahith Somasundar, Madireddy Tanishka, Gara Shanmukh Sai, B Nikhil Siddharth)

---

## 1. System Overview

CommercePulse++ ingests two categories of data — live user events (clickstreams, add-to-cart, checkouts) and batch business data (orders, inventory, campaigns) — processes them through separate but converging ETL pipelines, stores everything in a central analytics warehouse, and then applies machine learning models to generate actionable intelligence delivered via REST APIs and an interactive dashboard.

**Core capabilities:**
- Real-time conversion funnel tracking
- Product performance ranking
- Marketing channel attribution
- Demand forecasting
- Inventory risk alerting
- AI-generated optimization recommendations

---

## 2. Architecture Design

```
┌─────────────────────────────────────────────────────────────────┐
│                        DATA SOURCES                             │
│  Web/App Events (clicks, views, carts, checkouts)               │
│  Business Data (orders CSV, inventory exports, campaign reports) │
└───────────────┬─────────────────────────────┬───────────────────┘
                │                             │
                ▼                             ▼
┌──────────────────────┐         ┌──────────────────────┐
│  STREAMING PIPELINE  │         │    BATCH PIPELINE    │
│                      │         │                      │
│  Pub/Sub             │         │  Cloud Storage (GCS) │
│  → Dataflow          │         │  → Dataflow          │
│    (Apache Beam)     │         │    (Apache Beam)     │
│  → BigQuery          │         │  → BigQuery          │
│    (streaming insert)│         │    (batch load)      │
└──────────┬───────────┘         └──────────┬───────────┘
           │                                │
           └──────────────┬─────────────────┘
                          ▼
           ┌──────────────────────────────┐
           │      ANALYTICS WAREHOUSE     │
           │          BigQuery            │
           │  (raw → staging → mart)      │
           └──────────────┬───────────────┘
                          ▼
           ┌──────────────────────────────┐
           │   INTELLIGENCE / ML LAYER    │
           │  Vertex AI (AutoML + custom) │
           │  BigQuery ML                 │
           │  Cloud Composer (orchestrate)│
           └──────────────┬───────────────┘
                          ▼
           ┌──────────────────────────────┐
           │          API LAYER           │
           │  Cloud Run (FastAPI)         │
           │  Cloud Endpoints / API GW    │
           └──────────────┬───────────────┘
                          ▼
           ┌──────────────────────────────┐
           │       DASHBOARD LAYER        │
           │  Looker Studio / Looker      │
           │  React frontend (optional)   │
           └──────────────────────────────┘
```

---

## 3. Component Breakdown

| Component | GCP Service | Role |
|---|---|---|
| Event ingestion | Cloud Pub/Sub | Receive live clickstream events |
| Stream processing | Cloud Dataflow (Beam) | Transform, validate, enrich events |
| Batch ingestion | Cloud Storage (GCS) | Land raw CSV/JSON business files |
| Batch processing | Cloud Dataflow (Beam) | Parse, clean, load batch data |
| Data warehouse | BigQuery | Central analytics store |
| ML training & serving | Vertex AI | Demand forecasting, recommendations |
| In-warehouse ML | BigQuery ML | Attribution models, ranking |
| Orchestration | Cloud Composer (Airflow) | Schedule batch jobs and ML pipelines |
| API backend | Cloud Run (FastAPI) | Serve insights to frontend |
| API gateway | Cloud Endpoints | Auth, rate limiting, routing |
| Dashboard | Looker Studio | Pre-built visual analytics |
| Secrets | Secret Manager | API keys, DB credentials |
| CI/CD | Cloud Build + Artifact Registry | Automated deploy pipeline |
| Monitoring | Cloud Monitoring + Logging | Alerts, logs, SLOs |
| Identity | IAM + Workload Identity | Service-to-service auth |

---

## 4. Data Flow Through the Pipeline

### 4a. Streaming Pipeline (Live Events)

```
Browser/App SDK
  → HTTP POST to Cloud Run event collector
  → Publish to Pub/Sub topic: raw-events
  → Dataflow job: stream-etl
      - Parse JSON payload
      - Validate required fields (user_id, session_id, event_type, timestamp)
      - Enrich with product metadata lookup
      - Deduplicate within 10-minute window
      - Write to BigQuery table: raw.events (streaming insert)
```

### 4b. Batch Pipeline (Business Data)

```
Seller ERP / CRM / Ad Platforms
  → Export CSV/JSON to GCS bucket: gs://commercepulse-raw/
      - orders/YYYY-MM-DD/orders.csv
      - inventory/YYYY-MM-DD/inventory.csv
      - campaigns/YYYY-MM-DD/campaigns.csv
  → Cloud Composer triggers Dataflow job: batch-etl
      - Read files from GCS
      - Validate schema
      - Deduplicate on order_id / sku_id
      - Normalize currencies and timestamps
      - Write to BigQuery tables: raw.orders, raw.inventory, raw.campaigns
```

### 4c. Warehouse Transformation (dbt / SQL)

```
BigQuery raw layer
  → Staging models (clean, typed, renamed)
  → Mart models:
      - mart.funnel_events       (session-level funnel)
      - mart.product_performance (daily product metrics)
      - mart.attribution         (channel-level revenue)
      - mart.inventory_health    (stock levels + velocity)
      - mart.demand_signals      (aggregated demand features)
```

### 4d. Intelligence Layer

```
BigQuery mart tables
  → BigQuery ML: logistic regression for conversion probability
  → Vertex AI: ARIMA_PLUS for demand forecasting per SKU
  → Vertex AI: recommendation model for product affinity
  → Results written back to BigQuery: ml.predictions
```

### 4e. API + Dashboard

```
ml.predictions + mart tables
  → Cloud Run FastAPI reads from BigQuery via BigQuery client
  → Exposes REST endpoints
  → Looker Studio connects directly to BigQuery for dashboards
```

---

## 5. Technology Choices

| Category | Choice | Reason |
|---|---|---|
| Event streaming | Cloud Pub/Sub | Managed, scalable, integrates natively with Dataflow |
| Stream processing | Cloud Dataflow (Apache Beam, Python) | Serverless, auto-scaling, handles exactly-once semantics |
| Batch processing | Cloud Dataflow (Apache Beam, Python) | Same framework as streaming — unified codebase |
| Object storage | Cloud Storage (GCS) | Cheap, durable, direct BigQuery integration |
| Data warehouse | BigQuery | Serverless, columnar, supports streaming inserts and ML |
| Transformations | dbt Core on Cloud Composer | SQL-based, testable, version-controlled |
| ML platform | Vertex AI | Managed training, serving, experiment tracking |
| In-warehouse ML | BigQuery ML | No data movement, fast iteration |
| Orchestration | Cloud Composer (managed Airflow) | Industry standard, GCP-native DAG scheduling |
| API backend | Cloud Run + FastAPI | Serverless containers, auto-scale to zero |
| API gateway | Cloud Endpoints | Auth, quotas, OpenAPI spec enforcement |
| Dashboard | Looker Studio | Free, connects to BigQuery, shareable |
| CI/CD | Cloud Build | Native GCP, triggers on git push |
| Secrets | Secret Manager | Centralized, audited, IAM-controlled |
| Monitoring | Cloud Monitoring + Logging | Built-in GCP observability stack |
| IaC | Terraform | Reproducible infrastructure |

---

## 6. Programming Languages

| Layer | Language | Reason |
|---|---|---|
| Stream ETL | Python (Apache Beam) | Rich Beam SDK, data engineering standard |
| Batch ETL | Python (Apache Beam) | Unified with streaming |
| Warehouse transforms | SQL (dbt) | Declarative, testable, readable |
| ML models | Python (Vertex AI SDK, scikit-learn, TensorFlow) | ML ecosystem |
| API backend | Python (FastAPI) | Fast, typed, async-ready |
| Infrastructure | Terraform (HCL) | IaC standard |
| Dashboard config | Looker LookML (if using Looker) | Native Looker language |
| CI/CD pipelines | YAML (Cloud Build) | GCP standard |

---

## 7. Data Model Design

### Raw Layer (BigQuery dataset: `raw`)

**raw.events**
```sql
event_id        STRING NOT NULL,
session_id      STRING,
user_id         STRING,
anonymous_id    STRING,
event_type      STRING,   -- view, add_to_cart, checkout_start, purchase
product_id      STRING,
category        STRING,
price           FLOAT64,
quantity        INT64,
referrer        STRING,
utm_source      STRING,
utm_medium      STRING,
utm_campaign    STRING,
device_type     STRING,
country         STRING,
event_ts        TIMESTAMP NOT NULL,
ingested_at     TIMESTAMP
```

**raw.orders**
```sql
order_id        STRING NOT NULL,
user_id         STRING,
product_id      STRING,
sku_id          STRING,
quantity        INT64,
unit_price      FLOAT64,
discount_amount FLOAT64,
total_amount    FLOAT64,
channel         STRING,
order_status    STRING,
order_ts        TIMESTAMP,
ingested_at     TIMESTAMP
```

**raw.inventory**
```sql
sku_id          STRING NOT NULL,
product_id      STRING,
warehouse_id    STRING,
stock_qty       INT64,
reorder_point   INT64,
lead_time_days  INT64,
snapshot_date   DATE,
ingested_at     TIMESTAMP
```

**raw.campaigns**
```sql
campaign_id     STRING NOT NULL,
channel         STRING,
campaign_name   STRING,
spend           FLOAT64,
impressions     INT64,
clicks          INT64,
conversions     INT64,
revenue         FLOAT64,
campaign_date   DATE,
ingested_at     TIMESTAMP
```

### Mart Layer (BigQuery dataset: `mart`)

**mart.funnel_events** — one row per session per funnel stage
```sql
session_id, user_id, product_id, date,
viewed BOOL, added_to_cart BOOL, checkout_started BOOL, purchased BOOL,
drop_off_stage STRING, session_duration_sec INT64
```

**mart.product_performance** — daily product metrics
```sql
product_id, product_name, category, date,
views INT64, add_to_carts INT64, purchases INT64,
revenue FLOAT64, conversion_rate FLOAT64, return_rate FLOAT64,
avg_order_value FLOAT64, rank_by_revenue INT64
```

**mart.attribution** — channel-level attribution
```sql
channel, utm_source, utm_medium, campaign_id, date,
sessions INT64, conversions INT64, revenue FLOAT64,
cost FLOAT64, roas FLOAT64, cpa FLOAT64
```

**mart.inventory_health** — stock status per SKU
```sql
sku_id, product_id, warehouse_id, snapshot_date,
stock_qty INT64, avg_daily_sales FLOAT64, days_of_stock FLOAT64,
reorder_point INT64, risk_level STRING  -- low/medium/high/critical
```

### ML Layer (BigQuery dataset: `ml`)

**ml.demand_forecast** — per SKU per day
```sql
sku_id, forecast_date, predicted_units FLOAT64,
lower_bound FLOAT64, upper_bound FLOAT64, model_version STRING
```

**ml.conversion_scores** — per session
```sql
session_id, user_id, product_id, conversion_probability FLOAT64,
score_ts TIMESTAMP
```

---

## 8. Analytics Logic

### Conversion Funnel
```sql
-- Funnel drop-off rates per product category
SELECT
  category,
  COUNT(DISTINCT CASE WHEN viewed THEN session_id END)           AS views,
  COUNT(DISTINCT CASE WHEN added_to_cart THEN session_id END)    AS add_to_carts,
  COUNT(DISTINCT CASE WHEN checkout_started THEN session_id END) AS checkouts,
  COUNT(DISTINCT CASE WHEN purchased THEN session_id END)        AS purchases,
  SAFE_DIVIDE(
    COUNT(DISTINCT CASE WHEN purchased THEN session_id END),
    COUNT(DISTINCT CASE WHEN viewed THEN session_id END)
  ) AS end_to_end_conversion_rate
FROM mart.funnel_events
WHERE date BETWEEN DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY) AND CURRENT_DATE()
GROUP BY category
ORDER BY end_to_end_conversion_rate DESC;
```

### Product Performance Ranking
```sql
SELECT
  product_id, product_name, category,
  SUM(revenue) AS total_revenue,
  AVG(conversion_rate) AS avg_conversion_rate,
  RANK() OVER (PARTITION BY category ORDER BY SUM(revenue) DESC) AS revenue_rank
FROM mart.product_performance
WHERE date >= DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY)
GROUP BY 1, 2, 3;
```

### Inventory Risk Alert Logic
```sql
UPDATE mart.inventory_health
SET risk_level = CASE
  WHEN days_of_stock <= 3  THEN 'critical'
  WHEN days_of_stock <= 7  THEN 'high'
  WHEN days_of_stock <= 14 THEN 'medium'
  ELSE 'low'
END
WHERE snapshot_date = CURRENT_DATE();
```

### ROAS (Return on Ad Spend) by Channel
```sql
SELECT
  channel, utm_source,
  SUM(revenue) / NULLIF(SUM(cost), 0) AS roas,
  SUM(conversions) / NULLIF(SUM(clicks), 0) AS click_to_conversion_rate
FROM mart.attribution
WHERE date >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
GROUP BY 1, 2
ORDER BY roas DESC;
```

---

## 9. Machine Learning Capabilities

### 9a. Demand Forecasting (Vertex AI — ARIMA_PLUS via BigQuery ML)
- **Input:** daily sales per SKU (last 365 days)
- **Model:** `CREATE MODEL ml.demand_model OPTIONS(model_type='ARIMA_PLUS', time_series_id_col='sku_id', time_series_data_col='units_sold', time_series_timestamp_col='order_date')`
- **Output:** 30-day forecast per SKU with confidence intervals
- **Used for:** inventory risk alerts, reorder recommendations

### 9b. Conversion Probability (BigQuery ML — Logistic Regression)
- **Input features:** device_type, referrer, utm_source, product_category, price_bucket, session_depth, time_on_page
- **Label:** purchased (0/1)
- **Output:** probability score per active session
- **Used for:** real-time personalization signals, remarketing triggers

### 9c. Product Affinity / Recommendations (Vertex AI — Matrix Factorization)
- **Input:** user × product purchase history matrix
- **Output:** top-N recommended products per user
- **Used for:** "frequently bought together" and "you may also like" features

### 9d. Anomaly Detection (BigQuery ML — k-means clustering)
- **Input:** daily metric vectors per product (views, conversions, revenue)
- **Output:** outlier flag for products deviating significantly from cluster centroid
- **Used for:** surfacing sudden drops or spikes for seller attention

### Model Retraining Schedule (Cloud Composer)
- Demand forecast: daily at 02:00 UTC
- Conversion model: weekly Sunday 03:00 UTC
- Affinity model: weekly Saturday 03:00 UTC

---

## 10. API Design

**Base URL:** `https://api.commercepulse.example.com/v1`
**Auth:** Bearer token via Cloud Endpoints + Google IAP
**Format:** JSON

### Endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/funnel` | Conversion funnel metrics by category/date range |
| GET | `/products` | Product performance rankings |
| GET | `/products/{product_id}` | Single product deep-dive metrics |
| GET | `/attribution` | Marketing channel attribution summary |
| GET | `/inventory/risks` | Products at inventory risk (high/critical) |
| GET | `/forecast/{sku_id}` | 30-day demand forecast for a SKU |
| GET | `/recommendations/{user_id}` | Top product recommendations for a user |
| GET | `/insights/summary` | AI-generated text summary of top insights |
| POST | `/events` | Ingest a single live event (collector endpoint) |

### Sample Response — `/funnel`
```json
{
  "date_range": { "from": "2026-02-10", "to": "2026-03-11" },
  "funnel": [
    {
      "category": "Electronics",
      "views": 142000,
      "add_to_carts": 31200,
      "checkouts": 18400,
      "purchases": 9100,
      "conversion_rate": 0.064,
      "biggest_drop_off_stage": "add_to_cart_to_checkout"
    }
  ]
}
```

### Sample Response — `/inventory/risks`
```json
{
  "risks": [
    {
      "sku_id": "SKU-8821",
      "product_name": "Wireless Earbuds Pro",
      "stock_qty": 42,
      "avg_daily_sales": 18.3,
      "days_of_stock": 2.3,
      "risk_level": "critical",
      "forecast_demand_7d": 128
    }
  ]
}
```

---

## 11. Dashboard Functionality

Built in **Looker Studio** connected directly to BigQuery.

### Pages

| Page | Content |
|---|---|
| **Overview** | KPI cards: total revenue, orders, sessions, avg conversion rate. 30-day trend lines. |
| **Conversion Funnel** | Funnel chart by category. Drop-off % at each stage. Segment by device/channel. |
| **Product Performance** | Ranked table: revenue, conversion rate, views, returns. Filter by category/date. |
| **Marketing Attribution** | Bar chart: revenue by channel. ROAS table. Campaign comparison. |
| **Inventory Health** | Risk heatmap by SKU. Days-of-stock gauge. Reorder alerts table. |
| **Demand Forecast** | Line chart: actual vs forecast per SKU. Confidence band overlay. |
| **Recommendations** | Table of top affinity pairs. "Underperforming but high-traffic" product list. |
| **Alerts** | Live feed of critical inventory events, anomaly detections, sudden drop-offs. |

---

## 12. Infrastructure Layout

### GCP Project Structure
```
commercepulse-prod          (production)
commercepulse-dev           (development / testing)
commercepulse-shared        (shared: Artifact Registry, Secret Manager)
```

### GCP Services Per Region: `us-central1`

| Service | Resource Name |
|---|---|
| Pub/Sub | topic: raw-events, subscription: dataflow-stream-sub |
| GCS Buckets | commercepulse-raw, commercepulse-dataflow-temp, commercepulse-models |
| Dataflow | jobs: stream-etl, batch-etl |
| BigQuery | datasets: raw, staging, mart, ml |
| Cloud Run | services: event-collector, api-backend |
| Cloud Composer | environment: commercepulse-orchestrator |
| Vertex AI | endpoints: demand-forecast, conversion-score, affinity-model |
| Cloud Endpoints | api.commercepulse.example.com |
| Secret Manager | secrets: bq-sa-key, api-jwt-secret |
| Cloud Build | triggers: on push to main → deploy |
| Artifact Registry | repo: commercepulse-images |
| VPC | network: commercepulse-vpc, private service access enabled |

### IAM Service Accounts

| SA | Permissions |
|---|---|
| dataflow-worker@... | BigQuery dataEditor, Pub/Sub subscriber, GCS objectAdmin |
| composer-sa@... | BigQuery jobUser, Dataflow developer, Vertex AI user |
| cloudrun-api@... | BigQuery dataViewer, Vertex AI predictor |
| vertex-trainer@... | BigQuery dataViewer, GCS objectAdmin, Vertex AI admin |

---

## 13. Repository Structure

```
commercepulse-plus/
├── infra/                          # Terraform IaC
│   ├── main.tf
│   ├── variables.tf
│   ├── modules/
│   │   ├── bigquery/
│   │   ├── pubsub/
│   │   ├── dataflow/
│   │   ├── cloudrun/
│   │   └── composer/
│
├── pipelines/
│   ├── streaming/                  # Dataflow streaming ETL
│   │   ├── stream_etl.py           # Apache Beam pipeline
│   │   ├── transforms/
│   │   │   ├── validate.py
│   │   │   ├── enrich.py
│   │   │   └── deduplicate.py
│   │   └── requirements.txt
│   │
│   └── batch/                      # Dataflow batch ETL
│       ├── batch_etl.py
│       ├── transforms/
│       │   ├── orders.py
│       │   ├── inventory.py
│       │   └── campaigns.py
│       └── requirements.txt
│
├── warehouse/                      # dbt project
│   ├── dbt_project.yml
│   ├── profiles.yml
│   ├── models/
│   │   ├── staging/
│   │   │   ├── stg_events.sql
│   │   │   ├── stg_orders.sql
│   │   │   ├── stg_inventory.sql
│   │   │   └── stg_campaigns.sql
│   │   └── mart/
│   │       ├── mart_funnel_events.sql
│   │       ├── mart_product_performance.sql
│   │       ├── mart_attribution.sql
│   │       └── mart_inventory_health.sql
│   └── tests/
│
├── ml/                             # ML model code
│   ├── demand_forecast/
│   │   ├── train.py                # Vertex AI ARIMA_PLUS via BQML
│   │   └── predict.py
│   ├── conversion_model/
│   │   ├── train.py                # BQML logistic regression
│   │   └── predict.py
│   └── affinity_model/
│       ├── train.py                # Vertex AI matrix factorization
│       └── predict.py
│
├── api/                            # FastAPI Cloud Run backend
│   ├── main.py
│   ├── routers/
│   │   ├── funnel.py
│   │   ├── products.py
│   │   ├── attribution.py
│   │   ├── inventory.py
│   │   ├── forecast.py
│   │   └── recommendations.py
│   ├── services/
│   │   ├── bigquery_client.py
│   │   └── vertex_client.py
│   ├── Dockerfile
│   └── requirements.txt
│
├── orchestration/                  # Cloud Composer DAGs
│   ├── dags/
│   │   ├── batch_pipeline_dag.py
│   │   ├── dbt_transform_dag.py
│   │   └── ml_retrain_dag.py
│
├── collector/                      # Event collector Cloud Run service
│   ├── main.py                     # Receives events, publishes to Pub/Sub
│   ├── Dockerfile
│   └── requirements.txt
│
├── cloudbuild.yaml                 # CI/CD pipeline definition
└── README.md
```

---

## 14. Development Phases

### Phase 1 — Foundation (Weeks 1–2)
- Provision GCP project, IAM, VPC via Terraform
- Create BigQuery datasets and raw table schemas
- Set up Pub/Sub topic and GCS buckets
- Create Artifact Registry and Cloud Build triggers

### Phase 2 — Ingestion Pipelines (Weeks 3–4)
- Build and deploy streaming ETL (Dataflow + Beam)
- Build and deploy batch ETL (Dataflow + Beam)
- Validate raw data landing correctly in BigQuery

### Phase 3 — Warehouse Layer (Week 5)
- Set up dbt project connected to BigQuery
- Write staging models for all raw tables
- Write mart models: funnel, product, attribution, inventory
- Add dbt tests (not_null, unique, accepted_values)

### Phase 4 — ML Layer (Weeks 6–7)
- Train demand forecast model (BigQuery ML ARIMA_PLUS)
- Train conversion probability model (BigQuery ML logistic regression)
- Train affinity model (Vertex AI)
- Write prediction jobs and store results in `ml.*` tables

### Phase 5 — API Layer (Week 8)
- Build FastAPI application with all endpoints
- Containerize and deploy to Cloud Run
- Wire up Cloud Endpoints for auth and rate limiting
- Integration test all endpoints against BigQuery

### Phase 6 — Orchestration (Week 9)
- Write Cloud Composer DAGs for batch pipeline, dbt runs, ML retraining
- Schedule and test full end-to-end pipeline run

### Phase 7 — Dashboard (Week 10)
- Build all Looker Studio pages connected to BigQuery mart tables
- Add inventory risk alerts and anomaly indicators
- Share with stakeholders for feedback

### Phase 8 — Hardening (Weeks 11–12)
- Add Cloud Monitoring dashboards and SLO alerts
- Load and performance test API endpoints
- Security review: IAM least privilege, Secret Manager audit
- End-to-end integration testing with synthetic data

---

## 15. Step-by-Step Implementation Plan

### Step 1: Bootstrap Infrastructure
```bash
cd infra/
terraform init
terraform plan -var-file=prod.tfvars
terraform apply
```
Creates: GCP project structure, IAM SAs, VPC, GCS buckets, Pub/Sub, BigQuery datasets.

### Step 2: Deploy Event Collector
- Write `collector/main.py` — FastAPI app that accepts POST /events, validates payload, publishes to Pub/Sub
- Build Docker image, push to Artifact Registry
- Deploy to Cloud Run with `--no-allow-unauthenticated` (API key auth)

### Step 3: Deploy Streaming Dataflow Job
- Write `pipelines/streaming/stream_etl.py` using Apache Beam
- Test locally with DirectRunner
- Deploy to Dataflow with `DataflowRunner --streaming`

### Step 4: Configure Batch Ingestion
- Set up GCS bucket notification → Pub/Sub → Cloud Composer trigger
- Write batch ETL Beam pipeline for orders, inventory, campaigns
- Test with sample CSV files

### Step 5: Build dbt Transformations
```bash
cd warehouse/
dbt debug         # verify BigQuery connection
dbt run           # run all models
dbt test          # run all tests
```

### Step 6: Train ML Models
- Run `ml/demand_forecast/train.py` — executes BQML ARIMA_PLUS training
- Run `ml/conversion_model/train.py` — executes BQML logistic regression
- Register models in Vertex AI Model Registry

### Step 7: Deploy API Backend
- Write all FastAPI routers using BigQuery Python client
- Local test with `uvicorn main:app --reload`
- Deploy to Cloud Run
- Register with Cloud Endpoints (openapi.yaml)

### Step 8: Wire Orchestration
- Write Airflow DAGs in `orchestration/dags/`
- Upload to Cloud Composer GCS bucket
- Trigger test runs, validate end-to-end

### Step 9: Build Dashboards
- Connect Looker Studio to BigQuery mart dataset
- Build each page using mart table fields
- Set refresh schedule to every 4 hours

### Step 10: Enable Monitoring
- Create Cloud Monitoring uptime checks for API endpoints
- Set alerts: Dataflow job failures, BigQuery slot usage > 80%, Pub/Sub undelivered message age > 5 min
- Create log-based metrics for pipeline errors

---

## 16. Scaling Considerations

| Concern | Solution |
|---|---|
| High event volume (>10k events/sec) | Pub/Sub scales automatically; Dataflow auto-scales workers |
| BigQuery query costs | Use partitioned + clustered tables (partition by date, cluster by product_id) |
| API cold starts | Cloud Run min-instances = 1 for low-latency; connection pooling for BQ |
| ML retraining time | Vertex AI Training pipelines run async; results staged before swap |
| Multi-tenant sellers | Add `seller_id` partition key to all tables; row-level security via BigQuery RLS |
| Global latency | Deploy Cloud Run in multiple regions behind Global Load Balancer |
| dbt model refresh time | Use dbt incremental models for large fact tables |
| Dataflow backpressure | Set autoscaling maxWorkers; use persistent disk for shuffle |

---

## 17. Testing and Monitoring Strategy

### Unit Tests
- Beam pipeline transforms tested with `TestPipeline` (DirectRunner)
- dbt models tested with `dbt test` (not_null, unique, referential integrity)
- FastAPI endpoints tested with `pytest` + `httpx` test client

### Integration Tests
- End-to-end: publish synthetic event → assert row appears in BigQuery within 60s
- Batch pipeline: upload test CSV → assert rows land in raw table
- API: call `/funnel` → assert valid JSON with expected fields

### Data Quality
- dbt tests on every mart model
- Great Expectations for raw layer schema validation (run in Composer DAG)
- BigQuery Data QnA (Dataplex) for continuous data profiling

### Monitoring Alerts (Cloud Monitoring)
| Alert | Threshold |
|---|---|
| Streaming pipeline lag | Pub/Sub oldest unacked message > 5 min |
| Dataflow job failed | Any job state = FAILED |
| API error rate | 5xx rate > 1% over 5 min |
| BigQuery slot exhaustion | Slot utilization > 85% |
| Inventory critical SKUs | New critical-risk SKUs > 0 (daily check) |
| ML model staleness | Prediction table not updated in > 25 hours |

### SLOs
- Event collector availability: 99.9%
- API P95 latency: < 300ms
- Dashboard data freshness: < 4 hours behind real-time
- Demand forecast coverage: 100% of active SKUs forecasted daily

---

## Summary: Google Cloud Stack Used

| Layer | Google Service |
|---|---|
| Event streaming | Cloud Pub/Sub |
| Stream processing | Cloud Dataflow (Beam) |
| Batch processing | Cloud Dataflow (Beam) |
| Object storage | Cloud Storage |
| Data warehouse | BigQuery |
| ML training | Vertex AI + BigQuery ML |
| ML serving | Vertex AI Endpoints |
| Orchestration | Cloud Composer (Airflow) |
| API hosting | Cloud Run |
| API management | Cloud Endpoints |
| Dashboard | Looker Studio |
| CI/CD | Cloud Build + Artifact Registry |
| Secrets | Secret Manager |
| Monitoring | Cloud Monitoring + Cloud Logging |
| IaC | Terraform (GCP provider) |
| Identity | Google IAM + Workload Identity |

---

---

## 18. Key Design Decisions vs Azure Implementation

The Google Squad implementation differs from the Azure implementation in the following intentional ways:

| Concern | Azure Implementation | Google Implementation | Reason |
|---|---|---|---|
| Database | PostgreSQL (Supabase/pgvector) | BigQuery | BQ is optimized for analytical workloads; replaces both transactional store and vector store |
| Background tasks | Celery + Redis | Cloud Tasks + Cloud Composer + Vertex AI Pipelines | No worker process to manage; better observability and retry logic |
| LLM | LangGraph + Groq (Llama-3.1-8b) | Vertex AI Gemini 1.5 Pro | Fully Google Cloud-native; stronger grounded generation |
| Multi-agent pattern | LangGraph 6-node graph (orchestrator → revenue → operations → customer → marketing → synthesizer) | Sequential Vertex AI Pipeline DAG steps (equivalent node responsibilities) | Keeps everything within GCP ecosystem |
| Streaming | No real-time streaming lane | Pub/Sub → Dataflow → BigQuery streaming insert | Enables real-time conversion funnel analysis |
| Embeddings | sentence-transformers (all-MiniLM-L6-v2, 384 dims) in-code | BQML `ML.GENERATE_TEXT_EMBEDDING` (768 dims) stored in BigQuery | No external vector DB needed; similarity via `ML.DISTANCE` |
| Column mapping | `ingestion.py` ORDER_COL_MAP / INVENTORY_COL_MAP etc. | **Directly reused** in `GOOGLE/pipelines/batch/col_maps.py` | No changes needed — same alias logic applies |

---

## 19. Critical Files to Reuse from Azure Implementation

These Azure files should be ported directly into the Google implementation rather than rewritten from scratch:

| Azure File | Port Target | What to Reuse |
|---|---|---|
| `AZURE/backend/app/services/ingestion.py` | `GOOGLE/pipelines/batch/col_maps.py` | All five column alias maps (ORDER_COL_MAP, INVENTORY_COL_MAP, PRICING_COL_MAP, TRAFFIC_COL_MAP, LOGISTICS_COL_MAP) and pandas parsing logic inside Beam DoFns |
| `AZURE/backend/app/models/models.py` | BigQuery table DDL (Terraform `modules/bigquery/main.tf`) | All five domain entity schemas → translate to BQ table schemas with equivalent partitioning and clustering |
| `AZURE/backend/app/routes/analytics.py` | `GOOGLE/backend/app/services/analytics_queries.py` | All analytics SQL queries (revenue, funnel, inventory alerts, pricing margins, logistics RTO) — port from PostgreSQL to BigQuery Standard SQL (replace `::numeric` with `CAST`, `FILTER (WHERE ...)` with `COUNTIF`) |
| `AZURE/ai_agents/app/agents/schemas.py` | `GOOGLE/backend/app/services/gemini_service.py` | `RevenueInsights`, `OperationsInsights`, `MarketInsights`, `MarketingInsights`, `ExecutiveActionPlan` Pydantic schemas → reuse as structured output format for Gemini API calls |
| `AZURE/ai_agents/app/agents/graph.py` | `GOOGLE/ml/pipelines/demand_forecast_pipeline.py` (pattern) | The 6-node agent flow logic → translate into sequential Vertex AI Pipeline DAG with equivalent step responsibilities |

---

*Blueprint version 1.0 — CommercePulse++ Google Squad*
