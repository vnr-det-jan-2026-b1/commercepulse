# CommercePulse — Google Cloud Squad

A full-stack e-commerce analytics platform built on Google Cloud. The platform consists of two web apps and a shared FastAPI backend deployed on Cloud Run, with BigQuery as the analytics engine.

---

## Architecture

```
NovaCart (localhost:5174)
  └── Browse products, add to cart, place orders
        └── POST /v1/events  ──────────────────────────────────┐
                                                               ▼
                                              BigQuery: cp_raw.storefront_events
                                                               │
NovaAdmin (localhost:5173)                                     │
  └── Overview / Analytics / Recommendations / Products        │
        └── GET /v1/analytics/*  ◄──────── FastAPI (Cloud Run) ┘
```

**Backend:** `https://commercepulse-backend-292190719930.asia-south1.run.app`

---

## Apps

### NovaCart — Customer Storefront
Electronics store where customers browse, filter, and purchase products. All user actions (page views, product views, cart adds, purchases) are streamed to BigQuery in real time.

**Features:**
- 12 products across 5 categories (Audio, Accessories, Wearables, Peripherals, Smart Home)
- Hero banner + category filter bar
- Live stock badges on every product card (green / amber / red)
- Product detail page with qty selector, trust badges, and sold-out handling
- Cart drawer with order summary, free delivery above ₹999
- Stock refreshes automatically after every purchase

### NovaAdmin — Seller Analytics Portal
Real-time analytics dashboard for the seller to monitor storefront performance, track inventory, and act on AI-generated product recommendations.

**Tabs:**
| Tab | What it shows |
|---|---|
| Overview | KPI cards (visits, revenue, cart adds, conversion rate) + inventory health summary |
| Analytics | Hourly / daily traffic line chart, conversion funnel, key metrics — with Today / 7d / 30d filter |
| Recommendations | Demand-scored recommendation cards sorted by urgency |
| Products | Inventory table with stock bars + full performance metrics table |

---

## Product Catalog (12 Products)

| ID | Name | Category | Price |
|---|---|---|---|
| P001 | Wireless Earbuds Pro | Audio | ₹2,999 |
| P002 | 20W Fast Charger | Accessories | ₹799 |
| P003 | Smartwatch Series X | Wearables | ₹8,499 |
| P004 | Mechanical Keyboard | Peripherals | ₹3,499 |
| P005 | Portable Power Bank 20000mAh | Accessories | ₹1,799 |
| P006 | Noise-Cancelling Headphones | Audio | ₹5,999 |
| P007 | Portable Bluetooth Speaker | Audio | ₹2,299 |
| P008 | USB-C Hub 7-in-1 | Accessories | ₹1,499 |
| P009 | Gaming Mouse RGB | Peripherals | ₹1,299 |
| P010 | 4K Webcam Pro | Peripherals | ₹4,999 |
| P011 | Fitness Tracker Band | Wearables | ₹3,299 |
| P012 | Smart LED Desk Lamp | Smart Home | ₹1,999 |

Each product starts with **10 units** of stock (`cp_raw.product_catalog`). Stock decreases in real time as purchases are made.

---

## Recommendation Engine

Every product receives a **demand score** and one of six recommendation types, calculated from BigQuery event data.

**Demand Score Formula:**
```
demand_score = views × 0.2 + cart_adds × 0.5 + purchases × 1.0
```

**Recommendation Logic:**

| Type | Condition | Action |
|---|---|---|
| 🔴 RESTOCK_URGENT | stock ≤ 2 AND demand ≥ 1 | Restock immediately — selling fast |
| 🟠 RESTOCK_SOON | stock ≤ 4 AND demand ≥ 0.5 | Restock within 3–5 days |
| 🟢 INCREASE_PRICE | views ≥ 5 AND conversion ≥ 20% | High demand — raise price 10–15% |
| 🔵 DISCOUNT | views ≥ 4 AND conversion < 5% | Low conversion — offer 10% discount |
| ⚪ DONT_RESTOCK | views < 2 AND purchases = 0 | Low interest — skip restocking |
| ✅ MAINTAIN | everything else | Performing well — maintain strategy |

---

## BigQuery Tables

| Dataset | Table | Purpose |
|---|---|---|
| `cp_raw` | `storefront_events` | Raw event stream from NovaCart |
| `cp_raw` | `product_catalog` | Product master + initial stock (10 units each) |

**`storefront_events` schema:**
```
event_id STRING, event_type STRING, session_id STRING, seller_id STRING,
product_id STRING, product_name STRING, category STRING,
price FLOAT64, quantity INT64, ts TIMESTAMP
```

**`product_catalog` schema:**
```
product_id STRING, product_name STRING, category STRING,
price FLOAT64, initial_stock INT64, seller_id STRING
```

**Current stock** is derived at query time:
```sql
current_stock = initial_stock - SUM(purchase quantities from storefront_events)
```

---

## API Endpoints

**Base URL:** `https://commercepulse-backend-292190719930.asia-south1.run.app`

All analytics endpoints require `?seller_id=SELLER_001`.

| Method | Path | Description |
|---|---|---|
| POST | `/v1/events` | Ingest storefront event (no auth) |
| GET | `/v1/analytics/storefront` | Overview, traffic, products, funnel. Params: `days`, `granularity=day\|hour` |
| GET | `/v1/analytics/stock` | Current stock per product |
| GET | `/v1/analytics/recommendations` | Demand-based recommendations. Param: `days` |

---

## Local Setup

### Prerequisites
- Node.js 18+
- Python 3.11+
- Google Cloud credentials with BigQuery access

### Backend (FastAPI)
```bash
cd backend
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Set in `backend/.env`:
```
GCP_PROJECT=commercepulse-project
BQ_DATASET_RAW=cp_raw
```

### NovaCart (Storefront)
```bash
cd storefront
npm install
npm run dev          # http://localhost:5174
```

Set in `storefront/.env`:
```
VITE_API_URL=https://commercepulse-backend-292190719930.asia-south1.run.app
VITE_SELLER_ID=SELLER_001
```

### NovaAdmin (Analytics Dashboard)
```bash
cd frontend
npm install
npm run dev          # http://localhost:5173
```

Set in `frontend/.env`:
```
VITE_API_URL=https://commercepulse-backend-292190719930.asia-south1.run.app
VITE_SELLER_ID=SELLER_001
```

---

## Backend Deployment (Cloud Run)

```bash
cd backend
gcloud run deploy commercepulse-backend \
  --source . \
  --region asia-south1 \
  --allow-unauthenticated \
  --project commercepulse-project
```

The service account `sa-cloudrun-api@commercepulse-project.iam.gserviceaccount.com` requires `roles/bigquery.dataEditor` at the project level for streaming inserts to work.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | FastAPI + Python, deployed on Google Cloud Run |
| Analytics DB | Google BigQuery |
| Storefront | React + TypeScript + Vite + Tailwind CSS |
| Admin Dashboard | React + TypeScript + Vite + Tailwind CSS + Recharts |
| Data Fetching | TanStack React Query (30s auto-refresh) |
| Event Tracking | Fire-and-forget fetch to `/v1/events` |
| GCP Project | `commercepulse-project` · Region: `asia-south1` |

---

## Event Flow

1. User visits NovaCart → `page_view` event fires
2. User opens a product → `product_view` event fires
3. User clicks "Add to Cart" → `add_to_cart` event fires
4. User places order → `purchase` event fires, cart clears, stock refreshes after 2s
5. All events stream to `cp_raw.storefront_events` via BigQuery streaming insert
6. NovaAdmin queries aggregated data every 30 seconds and displays live analytics
