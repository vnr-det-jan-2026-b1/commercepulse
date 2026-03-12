"""
CommercePulse++ API Tests
Uses FastAPI TestClient with mocked BigQuery — no GCP connection needed.

Usage:
    cd GOOGLE
    pytest tests/test_api.py -v
"""
import os
import sys
import pytest
from unittest.mock import AsyncMock, patch

# Point to backend app
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../backend"))
os.environ.setdefault("CP_DEV_MODE", "true")
os.environ.setdefault("GCP_PROJECT", "commercepulse-test")

from fastapi.testclient import TestClient
from app.main import app

SELLER = "test-seller-001"
HEADERS = {"X-Seller-Id": SELLER}


# ── Mock BigQuery responses ────────────────────────────────────

MOCK_DASHBOARD = {
    "total_net_revenue": 1234567.89,
    "total_orders": 4200,
    "cancellation_rate_pct": 3.2,
    "returned_orders": 85,
    "stockout_count": 2,
    "low_stock_count": 7,
    "rto_rate_pct": 5.1,
    "avg_roas": 3.8,
    "computed_at": "2026-03-12T00:00:00",
}

MOCK_REVENUE_ROWS = [
    {"marketplace": "flipkart",  "gross_revenue": 800000, "net_revenue": 720000,
     "total_discount": 40000, "total_orders": 2100, "delivered_orders": 1950,
     "cancelled_orders": 80, "returned_orders": 50, "avg_order_value": 380.95},
    {"marketplace": "amazon_in", "gross_revenue": 500000, "net_revenue": 460000,
     "total_discount": 20000, "total_orders": 1400, "delivered_orders": 1300,
     "cancelled_orders": 55, "returned_orders": 30, "avg_order_value": 357.14},
]

MOCK_TREND_ROWS = [
    {"order_date": "2026-03-10", "total_orders": 142, "revenue": 54180, "delivered": 132, "cancelled": 5},
    {"order_date": "2026-03-11", "total_orders": 158, "revenue": 60164, "delivered": 147, "cancelled": 7},
    {"order_date": "2026-03-12", "total_orders": 134, "revenue": 51012, "delivered": 124, "cancelled": 4},
]

MOCK_ALERTS = [
    {"sku": "SKU-0003", "marketplace": "flipkart",  "available_stock": 5,
     "reserved_stock": 2, "reorder_threshold": 20, "days_until_stockout": 2.1,
     "recommended_reorder_qty": 150, "risk_level": "CRITICAL", "score_date": "2026-03-12"},
    {"sku": "SKU-0007", "marketplace": "amazon_in", "available_stock": 12,
     "reserved_stock": 1, "reorder_threshold": 20, "days_until_stockout": 5.8,
     "recommended_reorder_qty": 80, "risk_level": "HIGH", "score_date": "2026-03-12"},
]

MOCK_INVENTORY_STATUS = [
    {"sku": "SKU-0003", "marketplace": "flipkart", "available_stock": 5,
     "reserved_stock": 2, "reorder_threshold": 20, "days_of_stock": 2.1,
     "warehouse_location": "BOM-WH1", "snapshot_date": "2026-03-12"},
]

MOCK_PRICING = [
    {"sku": "SKU-0001", "marketplace": "flipkart", "selling_price": 999.0,
     "cost_price": 420.0, "mrp": 1299.0, "commission_pct": 8.5,
     "commission_amount": 84.9, "discount_percentage": 23.1,
     "net_margin": 494.1, "margin_pct": 49.5, "snapshot_date": "2026-03-12"},
]

MOCK_FUNNEL_OVERALL = [
    {"metric_date": "2026-03-12", "impressions": 52000, "product_views": 18400,
     "add_to_cart": 3200, "checkout_starts": 1800, "purchases": 920,
     "avg_conversion_rate_pct": 5.0, "avg_roas": 3.8},
]

MOCK_FUNNEL_PRODUCT = [
    {"sku": "SKU-0001", "marketplace": "flipkart", "total_impressions": 12000,
     "total_clicks": 840, "total_add_to_cart": 210, "total_purchases": 88,
     "ctr_pct": 7.0, "conversion_rate_pct": 10.5, "click_to_cart_pct": 25.0,
     "total_ad_spend": 4200.0, "total_revenue_from_ads": 87912.0, "roas": 20.93},
]

MOCK_LOGISTICS = [
    {"marketplace": "flipkart", "total_shipments": 2100, "rto_count": 105,
     "rto_rate_pct": 5.0, "delivered": 1950, "avg_shipping_days": 4.2,
     "fulfillment_type": "seller"},
]

MOCK_RISK = [
    {"sku": "SKU-0003", "marketplace": "flipkart", "available_stock": 5,
     "reserved_stock": 0, "avg_daily_units": 2.4, "days_until_stockout": 2.1,
     "recommended_reorder_qty": 67, "risk_level": "CRITICAL", "score_date": "2026-03-12"},
]

MOCK_FORECAST = [
    {"sku": "SKU-0001", "marketplace": "flipkart", "forecast_date": "2026-03-13",
     "predicted_units": 18.5, "lower_bound": 12.1, "upper_bound": 24.9,
     "model_version": "1.0"},
]

MOCK_ATTRIBUTION = [
    {"utm_source": "google", "utm_medium": "cpc", "utm_campaign": "spring-sale",
     "attribution_date": "2026-03-12", "attributed_sessions": 4200,
     "attributed_conversions": 840, "attributed_revenue": 319200.0,
     "ad_spend": 84000.0, "roas": 3.8, "shapley_weight": 0.42,
     "attribution_model": "last_click"},
]

MOCK_ANOMALIES = [
    {"alert_type": "REVENUE_ANOMALY", "sku": "SKU-0005", "marketplace": "flipkart",
     "metric_name": "daily_revenue", "metric_value": 1200.0, "baseline_value": 9800.0,
     "deviation_pct": -87.8, "severity": "HIGH",
     "alert_ts": "2026-03-12T08:00:00", "is_resolved": False},
]


def _mock_bq(single=None, many=None):
    """Return a context manager that patches bq.query and bq.query_single."""
    q_mock = AsyncMock(return_value=many or [])
    qs_mock = AsyncMock(return_value=single)
    return patch.multiple(
        "app.clients.bigquery_client",
        query=q_mock,
        query_single=qs_mock,
    )


# ── Fixtures ───────────────────────────────────────────────────

@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:
        yield c


# ── System ─────────────────────────────────────────────────────

def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "ok"
    assert "version" in data
    assert "project" in data


def test_root(client):
    r = client.get("/")
    assert r.status_code == 200


# ── Analytics endpoints ────────────────────────────────────────

def test_dashboard(client):
    with _mock_bq(single=MOCK_DASHBOARD):
        r = client.get(f"/v1/analytics/dashboard?seller_id={SELLER}", headers=HEADERS)
    assert r.status_code == 200
    data = r.json()
    assert data["seller_id"] == SELLER
    kpis = data["kpis"]
    assert kpis["total_net_revenue"] == pytest.approx(1234567.89)
    assert kpis["total_orders"] == 4200
    assert kpis["avg_roas"] == pytest.approx(3.8)
    assert "low_stock_products" in kpis


def test_revenue_summary(client):
    with _mock_bq(many=MOCK_REVENUE_ROWS):
        r = client.get(f"/v1/analytics/revenue?seller_id={SELLER}&days=30", headers=HEADERS)
    assert r.status_code == 200
    data = r.json()
    assert data["period_days"] == 30
    assert len(data["data"]) == 2
    assert data["data"][0]["marketplace"] == "flipkart"


def test_orders_trend(client):
    with _mock_bq(many=MOCK_TREND_ROWS):
        r = client.get(f"/v1/analytics/orders/trend?seller_id={SELLER}&days=7", headers=HEADERS)
    assert r.status_code == 200
    rows = r.json()["data"]
    assert len(rows) == 3
    assert rows[0]["order_date"] == "2026-03-10"
    assert rows[0]["total_orders"] == 142


def test_funnel(client):
    with patch("app.clients.bigquery_client.query",
               side_effect=[MOCK_FUNNEL_PRODUCT, MOCK_FUNNEL_OVERALL]):
        r = client.get(f"/v1/analytics/funnel?seller_id={SELLER}&days=7", headers=HEADERS)
    assert r.status_code == 200
    data = r.json()
    assert "overall_trend" in data
    assert "by_product" in data


def test_inventory_alerts(client):
    with _mock_bq(many=MOCK_ALERTS):
        r = client.get(f"/v1/analytics/inventory/alerts?seller_id={SELLER}", headers=HEADERS)
    assert r.status_code == 200
    data = r.json()
    assert data["alert_count"] == 2
    assert data["alerts"][0]["risk_level"] == "CRITICAL"
    assert data["alerts"][0]["sku"] == "SKU-0003"


def test_inventory_status(client):
    with _mock_bq(many=MOCK_INVENTORY_STATUS):
        r = client.get(f"/v1/analytics/inventory/status?seller_id={SELLER}", headers=HEADERS)
    assert r.status_code == 200
    data = r.json()
    assert data["count"] == 1
    assert data["data"][0]["sku"] == "SKU-0003"


def test_pricing_margins(client):
    with _mock_bq(many=MOCK_PRICING):
        r = client.get(f"/v1/analytics/pricing/margins?seller_id={SELLER}", headers=HEADERS)
    assert r.status_code == 200
    data = r.json()
    assert data["count"] == 1
    assert data["data"][0]["margin_pct"] == pytest.approx(49.5)


def test_logistics_rto(client):
    with _mock_bq(many=MOCK_LOGISTICS):
        r = client.get(f"/v1/analytics/logistics/rto-rate?seller_id={SELLER}&days=30", headers=HEADERS)
    assert r.status_code == 200
    data = r.json()
    assert data["data"][0]["rto_rate_pct"] == pytest.approx(5.0)
    assert data["data"][0]["marketplace"] == "flipkart"


# ── Intelligence endpoints ─────────────────────────────────────

def test_inventory_risk(client):
    with _mock_bq(many=MOCK_RISK):
        r = client.get(f"/v1/intelligence/inventory-risk?seller_id={SELLER}", headers=HEADERS)
    assert r.status_code == 200
    data = r.json()
    assert data["summary"]["critical"] == 1
    assert data["risks"][0]["risk_level"] == "CRITICAL"
    assert data["risks"][0]["days_until_stockout"] == pytest.approx(2.1)


def test_demand_forecast(client):
    with _mock_bq(many=MOCK_FORECAST):
        r = client.get(
            f"/v1/intelligence/demand-forecast?seller_id={SELLER}&days_ahead=7",
            headers=HEADERS,
        )
    assert r.status_code == 200
    data = r.json()
    assert data["days_ahead"] == 7
    assert data["forecasts"][0]["predicted_units"] == pytest.approx(18.5)


def test_marketing_attribution(client):
    with _mock_bq(many=MOCK_ATTRIBUTION):
        r = client.get(
            f"/v1/intelligence/marketing-attribution?seller_id={SELLER}&model=last_click",
            headers=HEADERS,
        )
    assert r.status_code == 200
    data = r.json()
    assert data["attribution_model"] == "last_click"
    assert data["data"][0]["roas"] == pytest.approx(3.8)


def test_anomalies(client):
    with _mock_bq(many=MOCK_ANOMALIES):
        r = client.get(f"/v1/intelligence/anomalies?seller_id={SELLER}", headers=HEADERS)
    assert r.status_code == 200
    data = r.json()
    assert data["count"] == 1
    assert data["alerts"][0]["severity"] == "HIGH"


# ── Security (unit tests on the security module directly) ──────

def test_enforce_seller_scope_logic():
    """
    Test security logic: enforce_seller_scope should raise 403
    when seller_id query param != authenticated seller header.
    """
    import asyncio
    from fastapi import HTTPException
    from app.core import security

    original = security.DEV_MODE
    try:
        security.DEV_MODE = False  # simulate prod mode

        async def run():
            with pytest.raises(HTTPException) as exc_info:
                await security.enforce_seller_scope(
                    seller_id="different-seller",
                    auth_seller=SELLER,
                )
            assert exc_info.value.status_code == 403

        asyncio.run(run())
    finally:
        security.DEV_MODE = original  # restore


def test_unauthenticated_raises_401():
    """Missing auth header raises 401 in prod mode."""
    import asyncio
    from fastapi import HTTPException
    from app.core import security

    original = security.DEV_MODE
    try:
        security.DEV_MODE = False

        async def run():
            with pytest.raises(HTTPException) as exc_info:
                await security.enforce_seller_scope(
                    seller_id=SELLER,
                    auth_seller=None,
                )
            assert exc_info.value.status_code == 401

        asyncio.run(run())
    finally:
        security.DEV_MODE = original
