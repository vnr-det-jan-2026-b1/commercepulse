"""
Tests for the Dataflow batch ingestion pipeline (runs with DirectRunner — no GCP needed).

Usage:
    cd GOOGLE/pipelines/batch
    pip install apache-beam[gcp] pandas openpyxl pytest
    pytest ../../tests/test_pipeline.py -v
"""
import io
import sys
import os
import pytest
import pandas as pd

# Apache Beam does not yet support Python 3.14 — skip Beam tests gracefully
try:
    import apache_beam  # noqa: F401
    BEAM_AVAILABLE = True
except Exception:
    BEAM_AVAILABLE = False

beam_required = pytest.mark.skipif(
    not BEAM_AVAILABLE,
    reason="apache-beam not available on this Python version"
)

# Add batch pipeline to path
BATCH_DIR = os.path.join(os.path.dirname(__file__), "../pipelines/batch")
sys.path.insert(0, BATCH_DIR)

from col_maps import (
    ORDER_COL_MAP, INVENTORY_COL_MAP, PRICING_COL_MAP,
    TRAFFIC_COL_MAP, LOGISTICS_COL_MAP,
)
from transforms.parsers import (
    _normalise_columns, _parse_date, _safe_float, _safe_int, _safe_bool,
    _coerce_row, ParseExcelDoFn,
)


# ── Column map tests ───────────────────────────────────────────

def test_order_col_map_normalises_selling_price():
    df = pd.DataFrame([{"Selling Price": 999.0, "Order ID": "X001", "SKU": "S1", "Marketplace": "flipkart"}])
    result = _normalise_columns(df, ORDER_COL_MAP)
    assert "selling_price" in result.columns
    assert "external_order_id" in result.columns


def test_inventory_col_map_stock_aliases():
    df = pd.DataFrame([{"stock": 100, "sku": "S1", "marketplace": "flipkart"}])
    result = _normalise_columns(df, INVENTORY_COL_MAP)
    assert "available_stock" in result.columns


def test_traffic_col_map_add_to_cart():
    df = pd.DataFrame([{"add to cart": 5, "sku": "S1", "marketplace": "m1", "date": "2026-01-01"}])
    result = _normalise_columns(df, TRAFFIC_COL_MAP)
    assert "add_to_cart" in result.columns


# ── Helper function tests ──────────────────────────────────────

def test_parse_date_iso_string():
    assert _parse_date("2026-03-12") == "2026-03-12"


def test_parse_date_excel_serial():
    import datetime
    d = datetime.date(2026, 3, 12)
    assert _parse_date(d) == "2026-03-12"


def test_parse_date_none():
    assert _parse_date(None) is None
    assert _parse_date(float("nan")) is None


def test_safe_float():
    assert _safe_float("123.45") == 123.45
    assert _safe_float(None) == 0.0
    assert _safe_float("bad") == 0.0


def test_safe_int():
    assert _safe_int("42") == 42
    assert _safe_int(None) == 0


def test_safe_bool():
    assert _safe_bool("yes") is True
    assert _safe_bool("no")  is False
    assert _safe_bool(True)  is True
    assert _safe_bool(0)     is False


# ── Row coercion tests ─────────────────────────────────────────

def test_coerce_order_row_computes_net_revenue():
    row = {
        "sku":           "SKU-001",
        "marketplace":   "flipkart",
        "order_status":  "delivered",
        "selling_price": 999.0,
        "quantity":      2,
        "discount":      50.0,
        "order_date":    "2026-03-01",
    }
    result = _coerce_row(
        row, date_fields=["order_date", "delivery_date"],
        bool_fields=["return_flag"],
        seller_id="test-seller-001",
        snapshot_date="2026-03-12",
        domain="orders",
    )
    # net_revenue = (999 * 2) - 50 = 1948
    assert result["net_revenue"] == pytest.approx(1948.0)
    assert result["seller_id"] == "test-seller-001"


def test_coerce_pricing_row_computes_margin():
    row = {
        "sku":           "SKU-001",
        "marketplace":   "flipkart",
        "selling_price": 1000.0,
        "cost_price":    400.0,
        "commission_amount": 100.0,
        "snapshot_date": "2026-03-12",
    }
    result = _coerce_row(
        row, date_fields=["snapshot_date"], bool_fields=[],
        seller_id="test-seller-001",
        snapshot_date="2026-03-12",
        domain="pricing",
    )
    assert result["net_margin"] == pytest.approx(500.0)
    assert result["margin_pct"] == pytest.approx(50.0)


# ── ParseExcelDoFn tests (Apache Beam DirectRunner) ────────────

def _make_excel_bytes(df: pd.DataFrame) -> bytes:
    buf = io.BytesIO()
    df.to_excel(buf, index=False)
    return buf.getvalue()


@beam_required
def test_parse_excel_dofn_valid_orders():
    import apache_beam as beam
    from apache_beam.testing.test_pipeline import TestPipeline
    from apache_beam.testing.util import assert_that, is_not_empty

    df = pd.DataFrame([{
        "Order ID":      "ORD-001",
        "Marketplace":   "flipkart",
        "SKU":           "SKU-001",
        "Status":        "delivered",
        "Quantity":      2,
        "Selling Price": 999.0,
        "Cost Price":    450.0,
        "Discount":      50.0,
        "Tax":           179.82,
        "Shipping Fee":  60.0,
        "Order Date":    "2026-03-01",
    }])

    excel_bytes = _make_excel_bytes(df)

    with TestPipeline() as p:
        result = (
            p
            | beam.Create([excel_bytes])
            | beam.ParDo(ParseExcelDoFn(
                domain="orders",
                seller_id="test-seller-001",
                snapshot_date="2026-03-12",
            )).with_outputs(ParseExcelDoFn.DEAD_LETTER, main="valid")
        )
        assert_that(result.valid, is_not_empty(), label="check_valid_rows")


@beam_required
def test_parse_excel_dofn_missing_sku_goes_to_dead_letter():
    import apache_beam as beam
    from apache_beam.testing.test_pipeline import TestPipeline
    from apache_beam.testing.util import assert_that, is_not_empty

    df = pd.DataFrame([{
        "Marketplace":   "flipkart",
        # SKU missing on purpose
        "Status":        "delivered",
        "Selling Price": 999.0,
        "Order Date":    "2026-03-01",
    }])

    excel_bytes = _make_excel_bytes(df)

    with TestPipeline() as p:
        result = (
            p
            | beam.Create([excel_bytes])
            | beam.ParDo(ParseExcelDoFn(
                domain="orders",
                seller_id="test-seller-001",
                snapshot_date="2026-03-12",
            )).with_outputs(ParseExcelDoFn.DEAD_LETTER, main="valid")
        )
        assert_that(
            result[ParseExcelDoFn.DEAD_LETTER],
            is_not_empty(),
            label="check_dead_letter",
        )
