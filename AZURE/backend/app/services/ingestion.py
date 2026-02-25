"""
Excel Ingestion Service
Parses uploaded Excel sheets and bulk-inserts into PostgreSQL.
Each domain has its own parser that maps flexible column names to DB columns.
"""
import io
import uuid
from datetime import date, datetime
from typing import Optional

import pandas as pd
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.models.models import (
    Product, Order, InventorySnapshot, PricingSnapshot,
    TrafficMetric, LogisticsMetric,
)


# ── Column aliases ─────────────────────────────────────────────
# Maps flexible Excel column names → canonical DB column name
ORDER_COL_MAP = {
    "order id": "external_order_id", "order_id": "external_order_id",
    "marketplace": "marketplace",
    "sku": "sku", "product sku": "sku",
    "status": "order_status", "order_status": "order_status",
    "quantity": "quantity", "qty": "quantity",
    "selling price": "selling_price", "selling_price": "selling_price", "price": "selling_price",
    "cost price": "cost_price", "cost_price": "cost_price", "cogs": "cost_price",
    "discount": "discount",
    "tax": "tax",
    "shipping fee": "shipping_fee", "shipping_fee": "shipping_fee", "shipping": "shipping_fee",
    "order date": "order_date", "order_date": "order_date", "date": "order_date",
    "delivery date": "delivery_date", "delivery_date": "delivery_date",
    "return": "return_flag", "return_flag": "return_flag",
    "cancellation reason": "cancellation_reason", "cancellation_reason": "cancellation_reason",
}

INVENTORY_COL_MAP = {
    "sku": "sku", "product sku": "sku",
    "marketplace": "marketplace",
    "available stock": "available_stock", "available_stock": "available_stock", "stock": "available_stock",
    "reserved stock": "reserved_stock", "reserved_stock": "reserved_stock",
    "reorder threshold": "reorder_threshold", "reorder_threshold": "reorder_threshold",
    "days of stock": "days_of_stock", "days_of_stock": "days_of_stock",
    "warehouse": "warehouse_location", "warehouse_location": "warehouse_location",
    "snapshot date": "snapshot_date", "snapshot_date": "snapshot_date", "date": "snapshot_date",
}

PRICING_COL_MAP = {
    "sku": "sku", "product sku": "sku",
    "marketplace": "marketplace",
    "selling price": "selling_price", "selling_price": "selling_price",
    "cost price": "cost_price", "cost_price": "cost_price",
    "mrp": "mrp",
    "commission %": "commission_pct", "commission_pct": "commission_pct",
    "commission amount": "commission_amount", "commission_amount": "commission_amount",
    "discount %": "discount_percentage", "discount_percentage": "discount_percentage",
    "net margin": "net_margin", "net_margin": "net_margin",
    "margin %": "margin_pct", "margin_pct": "margin_pct",
    "snapshot date": "snapshot_date", "date": "snapshot_date",
}

TRAFFIC_COL_MAP = {
    "sku": "sku", "product sku": "sku",
    "marketplace": "marketplace",
    "date": "metric_date", "metric date": "metric_date", "metric_date": "metric_date",
    "impressions": "impressions",
    "clicks": "clicks",
    "add to cart": "add_to_cart", "add_to_cart": "add_to_cart",
    "orders": "orders",
    "ad spend": "ad_spend", "ad_spend": "ad_spend",
    "revenue from ads": "revenue_from_ads", "revenue_from_ads": "revenue_from_ads",
}

LOGISTICS_COL_MAP = {
    "order id": "external_order_id", "order_id": "external_order_id",
    "marketplace": "marketplace",
    "courier": "courier_name", "courier_name": "courier_name",
    "tracking id": "tracking_id", "tracking_id": "tracking_id",
    "fulfillment type": "fulfillment_type", "fulfillment_type": "fulfillment_type",
    "warehouse id": "warehouse_id", "warehouse_id": "warehouse_id",
    "dispatch date": "dispatch_date", "dispatch_date": "dispatch_date",
    "expected delivery": "expected_delivery",
    "actual delivery": "actual_delivery",
    "shipping days": "shipping_time_days", "shipping_time_days": "shipping_time_days",
    "delivery status": "delivery_status", "delivery_status": "delivery_status", "status": "delivery_status",
    "rto": "rto_flag", "rto_flag": "rto_flag",
    "rto reason": "rto_reason",
    "snapshot date": "snapshot_date", "date": "snapshot_date",
}


# ── Helpers ────────────────────────────────────────────────────

def _normalise_columns(df: pd.DataFrame, col_map: dict) -> pd.DataFrame:
    """Lower-case and strip column names, then rename using col_map."""
    df.columns = [c.strip().lower() for c in df.columns]
    rename = {k: v for k, v in col_map.items() if k in df.columns}
    return df.rename(columns=rename)


def _parse_date(val) -> Optional[date]:
    if pd.isna(val):
        return None
    if isinstance(val, (date, datetime)):
        return val if isinstance(val, date) else val.date()
    try:
        return pd.to_datetime(val).date()
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


async def _resolve_product(db: AsyncSession, seller_id: str, sku: str, marketplace: str) -> Optional[str]:
    """Resolve (seller_id, sku, marketplace) → product_id. Creates product if not exists."""
    result = await db.execute(
        select(Product.product_id).where(
            Product.seller_id == seller_id,
            Product.sku == sku,
            Product.marketplace == marketplace,
        )
    )
    row = result.scalar_one_or_none()
    if row:
        return str(row)
    # Auto-create the product from SKU
    new_product = Product(
        seller_id=seller_id,
        sku=sku,
        product_name=sku,  # Will be updated if product name column exists
        marketplace=marketplace,
    )
    db.add(new_product)
    await db.flush()
    return str(new_product.product_id)


# ── Domain Parsers ──────────────────────────────────────────────

async def ingest_orders(db: AsyncSession, file_bytes: bytes, seller_id: str, snapshot_date: date) -> dict:
    df = pd.read_excel(io.BytesIO(file_bytes), engine="openpyxl")
    df = _normalise_columns(df, ORDER_COL_MAP)

    rows_inserted = 0
    rows_skipped  = 0

    for _, row in df.iterrows():
        try:
            sku         = str(row.get("sku", "")).strip()
            marketplace = str(row.get("marketplace", "unknown")).strip()
            if not sku:
                rows_skipped += 1
                continue

            product_id = await _resolve_product(db, seller_id, sku, marketplace)

            order = Order(
                external_order_id   = str(row.get("external_order_id", "")) or None,
                seller_id           = seller_id,
                product_id          = product_id,
                marketplace         = marketplace,
                order_status        = str(row.get("order_status", "unknown")),
                quantity            = _safe_int(row.get("quantity"), 1),
                selling_price       = _safe_float(row.get("selling_price")),
                cost_price          = _safe_float(row.get("cost_price")) or None,
                discount            = _safe_float(row.get("discount")),
                tax                 = _safe_float(row.get("tax")),
                shipping_fee        = _safe_float(row.get("shipping_fee")),
                order_date          = _parse_date(row.get("order_date")) or snapshot_date,
                delivery_date       = _parse_date(row.get("delivery_date")),
                return_flag         = bool(row.get("return_flag", False)),
                cancellation_reason = str(row.get("cancellation_reason", "")) or None,
                snapshot_date       = snapshot_date,
            )
            db.add(order)
            rows_inserted += 1
        except Exception as e:
            rows_skipped += 1

    await db.commit()
    return {"inserted": rows_inserted, "skipped": rows_skipped, "domain": "orders"}


async def ingest_inventory(db: AsyncSession, file_bytes: bytes, seller_id: str, snapshot_date: date) -> dict:
    df = pd.read_excel(io.BytesIO(file_bytes), engine="openpyxl")
    df = _normalise_columns(df, INVENTORY_COL_MAP)

    rows_inserted = 0
    rows_skipped  = 0

    for _, row in df.iterrows():
        try:
            sku         = str(row.get("sku", "")).strip()
            marketplace = str(row.get("marketplace", "unknown")).strip()
            if not sku:
                rows_skipped += 1
                continue

            product_id = await _resolve_product(db, seller_id, sku, marketplace)
            snap_date  = _parse_date(row.get("snapshot_date")) or snapshot_date

            stmt = pg_insert(InventorySnapshot).values(
                seller_id         = seller_id,
                product_id        = product_id,
                marketplace       = marketplace,
                available_stock   = _safe_int(row.get("available_stock")),
                reserved_stock    = _safe_int(row.get("reserved_stock")),
                reorder_threshold = _safe_int(row.get("reorder_threshold"), 10),
                days_of_stock     = _safe_float(row.get("days_of_stock")) or None,
                warehouse_location= str(row.get("warehouse_location", "")) or None,
                snapshot_date     = snap_date,
            ).on_conflict_do_update(
                index_elements=["seller_id", "product_id", "marketplace", "snapshot_date"],
                set_={
                    "available_stock": _safe_int(row.get("available_stock")),
                    "reserved_stock": _safe_int(row.get("reserved_stock")),
                },
            )
            await db.execute(stmt)
            rows_inserted += 1
        except Exception:
            rows_skipped += 1

    await db.commit()
    return {"inserted": rows_inserted, "skipped": rows_skipped, "domain": "inventory"}


async def ingest_pricing(db: AsyncSession, file_bytes: bytes, seller_id: str, snapshot_date: date) -> dict:
    df = pd.read_excel(io.BytesIO(file_bytes), engine="openpyxl")
    df = _normalise_columns(df, PRICING_COL_MAP)

    rows_inserted = 0
    rows_skipped  = 0

    for _, row in df.iterrows():
        try:
            sku         = str(row.get("sku", "")).strip()
            marketplace = str(row.get("marketplace", "unknown")).strip()
            if not sku:
                rows_skipped += 1
                continue

            product_id  = await _resolve_product(db, seller_id, sku, marketplace)
            snap_date   = _parse_date(row.get("snapshot_date")) or snapshot_date
            sell_price  = _safe_float(row.get("selling_price"))
            cost_price  = _safe_float(row.get("cost_price")) or None
            comm_amount = _safe_float(row.get("commission_amount"))
            net_margin  = _safe_float(row.get("net_margin")) or (
                (sell_price - (cost_price or 0) - comm_amount) if cost_price else None
            )
            margin_pct  = _safe_float(row.get("margin_pct")) or (
                (net_margin / sell_price * 100) if net_margin and sell_price else None
            )

            stmt = pg_insert(PricingSnapshot).values(
                seller_id           = seller_id,
                product_id          = product_id,
                marketplace         = marketplace,
                selling_price       = sell_price,
                cost_price          = cost_price,
                mrp                 = _safe_float(row.get("mrp")) or None,
                commission_pct      = _safe_float(row.get("commission_pct")),
                commission_amount   = comm_amount,
                discount_percentage = _safe_float(row.get("discount_percentage")),
                net_margin          = net_margin,
                margin_pct          = margin_pct,
                snapshot_date       = snap_date,
            ).on_conflict_do_update(
                index_elements=["seller_id", "product_id", "marketplace", "snapshot_date"],
                set_={"selling_price": sell_price, "net_margin": net_margin, "margin_pct": margin_pct},
            )
            await db.execute(stmt)
            rows_inserted += 1
        except Exception:
            rows_skipped += 1

    await db.commit()
    return {"inserted": rows_inserted, "skipped": rows_skipped, "domain": "pricing"}


async def ingest_traffic(db: AsyncSession, file_bytes: bytes, seller_id: str, snapshot_date: date) -> dict:
    df = pd.read_excel(io.BytesIO(file_bytes), engine="openpyxl")
    df = _normalise_columns(df, TRAFFIC_COL_MAP)

    rows_inserted = 0
    rows_skipped  = 0

    for _, row in df.iterrows():
        try:
            sku         = str(row.get("sku", "")).strip()
            marketplace = str(row.get("marketplace", "unknown")).strip()
            if not sku:
                rows_skipped += 1
                continue

            product_id  = await _resolve_product(db, seller_id, sku, marketplace)
            metric_date = _parse_date(row.get("metric_date")) or snapshot_date

            stmt = pg_insert(TrafficMetric).values(
                seller_id        = seller_id,
                product_id       = product_id,
                marketplace      = marketplace,
                metric_date      = metric_date,
                impressions      = _safe_int(row.get("impressions")),
                clicks           = _safe_int(row.get("clicks")),
                add_to_cart      = _safe_int(row.get("add_to_cart")),
                orders           = _safe_int(row.get("orders")),
                ad_spend         = _safe_float(row.get("ad_spend")),
                revenue_from_ads = _safe_float(row.get("revenue_from_ads")),
            ).on_conflict_do_update(
                index_elements=["seller_id", "product_id", "marketplace", "metric_date"],
                set_={
                    "impressions": _safe_int(row.get("impressions")),
                    "clicks": _safe_int(row.get("clicks")),
                    "ad_spend": _safe_float(row.get("ad_spend")),
                },
            )
            await db.execute(stmt)
            rows_inserted += 1
        except Exception:
            rows_skipped += 1

    await db.commit()
    return {"inserted": rows_inserted, "skipped": rows_skipped, "domain": "traffic"}


async def ingest_logistics(db: AsyncSession, file_bytes: bytes, seller_id: str, snapshot_date: date) -> dict:
    df = pd.read_excel(io.BytesIO(file_bytes), engine="openpyxl")
    df = _normalise_columns(df, LOGISTICS_COL_MAP)

    rows_inserted = 0
    rows_skipped  = 0

    for _, row in df.iterrows():
        try:
            marketplace = str(row.get("marketplace", "unknown")).strip()

            # Resolve order_id if external_order_id present
            ext_order_id = str(row.get("external_order_id", "")).strip() or None

            logic_row = LogisticsMetric(
                seller_id          = seller_id,
                marketplace        = marketplace,
                courier_name       = str(row.get("courier_name", "")) or None,
                tracking_id        = str(row.get("tracking_id", "")) or None,
                fulfillment_type   = str(row.get("fulfillment_type", "seller")),
                warehouse_id       = str(row.get("warehouse_id", "")) or None,
                dispatch_date      = _parse_date(row.get("dispatch_date")),
                expected_delivery  = _parse_date(row.get("expected_delivery")),
                actual_delivery    = _parse_date(row.get("actual_delivery")),
                shipping_time_days = _safe_int(row.get("shipping_time_days")) or None,
                delivery_status    = str(row.get("delivery_status", "unknown")),
                rto_flag           = bool(row.get("rto_flag", False)),
                rto_reason         = str(row.get("rto_reason", "")) or None,
                snapshot_date      = _parse_date(row.get("snapshot_date")) or snapshot_date,
            )
            db.add(logic_row)
            rows_inserted += 1
        except Exception:
            rows_skipped += 1

    await db.commit()
    return {"inserted": rows_inserted, "skipped": rows_skipped, "domain": "logistics"}
