"""
Apache Beam DoFns for parsing and normalising Excel/CSV uploads.
Adapted from AZURE ingestion logic for use in Dataflow batch pipeline.
"""
import io
import uuid
import logging
from datetime import date, datetime
from typing import Optional

try:
    import apache_beam as beam
    _BEAM_AVAILABLE = True
except ImportError:
    _BEAM_AVAILABLE = False
    beam = None  # type: ignore[assignment]

import pandas as pd

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from col_maps import DOMAIN_CONFIG

logger = logging.getLogger(__name__)


# ── Helpers ────────────────────────────────────────────────────

def _normalise_columns(df: pd.DataFrame, col_map: dict) -> pd.DataFrame:
    df.columns = [c.strip().lower() for c in df.columns]
    rename = {k: v for k, v in col_map.items() if k in df.columns}
    return df.rename(columns=rename)


def _parse_date(val) -> Optional[str]:
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return None
    if isinstance(val, (date, datetime)):
        d = val if isinstance(val, date) else val.date()
        return d.isoformat()
    try:
        return pd.to_datetime(val).date().isoformat()
    except Exception:
        return None


def _safe_float(val, default=0.0) -> float:
    try:
        return float(val) if not pd.isna(val) else default
    except Exception:
        return default


def _safe_int(val, default=0) -> int:
    try:
        return int(val) if not pd.isna(val) else default
    except Exception:
        return default


def _safe_bool(val) -> bool:
    if isinstance(val, bool):
        return val
    if isinstance(val, str):
        return val.strip().lower() in ("true", "yes", "1", "y")
    try:
        return bool(int(val))
    except Exception:
        return False


# ── BigQuery schema coercion per domain ────────────────────────

def _coerce_row(row: dict, date_fields: list, bool_fields: list,
                seller_id: str, snapshot_date: str, domain: str) -> dict:
    """Convert parsed pandas row dict into a BQ-ready dict."""
    out = {"seller_id": seller_id, "ingest_timestamp": datetime.utcnow().isoformat()}

    for k, v in row.items():
        if k in date_fields:
            out[k] = _parse_date(v) or snapshot_date
        elif k in bool_fields:
            out[k] = _safe_bool(v)
        elif isinstance(v, float):
            out[k] = _safe_float(v)
        elif isinstance(v, int):
            out[k] = _safe_int(v)
        else:
            out[k] = str(v).strip() if v is not None and not (isinstance(v, float) and pd.isna(v)) else None

    # Compute net_revenue for orders
    if domain == "orders":
        qty = _safe_int(row.get("quantity"), 1)
        price = _safe_float(row.get("selling_price"))
        discount = _safe_float(row.get("discount"))
        out["net_revenue"] = round((price * qty) - discount, 2)
        out.setdefault("order_date", snapshot_date)

    # Compute margin for pricing
    if domain == "pricing":
        sell = _safe_float(row.get("selling_price"))
        cost = _safe_float(row.get("cost_price")) or None
        comm = _safe_float(row.get("commission_amount"))
        if sell and cost and "net_margin" not in row:
            out["net_margin"] = round(sell - cost - comm, 2)
        if sell and out.get("net_margin") and "margin_pct" not in row:
            out["margin_pct"] = round(out["net_margin"] / sell * 100, 2)

    return out


# ── DoFns ──────────────────────────────────────────────────────

_DoFnBase = beam.DoFn if _BEAM_AVAILABLE else object

class ParseExcelDoFn(_DoFnBase):
    """Reads an Excel/CSV file from GCS bytes and emits one dict per row."""

    DEAD_LETTER = "dead_letter"

    def __init__(self, domain: str, seller_id: str, snapshot_date: str):
        self.domain = domain
        self.seller_id = seller_id
        self.snapshot_date = snapshot_date

    def process(self, file_bytes: bytes):
        col_map, required_fields, date_fields, bool_fields = DOMAIN_CONFIG[self.domain]

        def _dead_letter(payload):
            if _BEAM_AVAILABLE:
                return beam.pvalue.TaggedOutput(self.DEAD_LETTER, payload)
            return None  # no-op when running without Beam

        try:
            df = pd.read_excel(io.BytesIO(file_bytes), engine="openpyxl")
        except Exception:
            try:
                df = pd.read_csv(io.BytesIO(file_bytes))
            except Exception as e:
                dl = _dead_letter({"error": f"Could not parse file: {e}",
                                   "domain": self.domain, "seller_id": self.seller_id})
                if dl is not None:
                    yield dl
                return

        df = _normalise_columns(df, col_map)

        for _, row in df.iterrows():
            row_dict = row.to_dict()

            # Check required fields
            missing = [f for f in required_fields if not row_dict.get(f)]
            if missing:
                dl = _dead_letter({"error": f"Missing required fields: {missing}",
                                   "domain": self.domain,
                                   "row": {k: str(v) for k, v in row_dict.items()}})
                if dl is not None:
                    yield dl
                continue

            try:
                coerced = _coerce_row(
                    row_dict, date_fields, bool_fields,
                    self.seller_id, self.snapshot_date, self.domain,
                )
                yield coerced
            except Exception as e:
                dl = _dead_letter({"error": str(e), "domain": self.domain,
                                   "row": {k: str(v) for k, v in row_dict.items()}})
                if dl is not None:
                    yield dl
