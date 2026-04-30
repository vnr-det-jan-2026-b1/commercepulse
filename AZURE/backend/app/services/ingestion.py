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
    "order id": "external_order_id", "order_id": "external_order_id", "id": "external_order_id",
    "marketplace": "marketplace", "platform": "marketplace", "channel": "marketplace",
    "sku": "sku", "product sku": "sku", "item sku": "sku",
    "status": "order_status", "order_status": "order_status", "order status": "order_status",
    "quantity": "quantity", "qty": "quantity", "qty.": "quantity",
    "selling price": "selling_price", "selling_price": "selling_price", "price": "selling_price", "amount": "selling_price",
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
    "snapshot date": "snapshot_date", "date": "snapshot_date",
}

TRAFFIC_COL_MAP = {
    "sku": "sku", "product sku": "sku",
    "marketplace": "marketplace",
    "date": "metric_date", "metric date": "metric_date", "metric_date": "metric_date",
    "impressions": "impressions",
    "clicks": "clicks",
    "sessions": "sessions",
    "page views": "page_views", "page_views": "page_views",
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
    "delivery status": "delivery_status", "delivery_status": "delivery_status", "status": "delivery_status",
    "rto": "rto_flag", "rto_flag": "rto_flag",
    "rto reason": "rto_reason",
    "snapshot date": "snapshot_date", "date": "snapshot_date",
}


# ── Helpers ────────────────────────────────────────────────────

def _normalise_columns(df: pd.DataFrame, col_map: dict) -> pd.DataFrame:
    """Lower-case, replace underscores with spaces, and intelligently map columns."""
    rename = {}
    for original_col in df.columns:
        c = str(original_col).strip().lower()
        c_space = c.replace("_", " ")

        # 1. Exact match
        if c in col_map:
            rename[original_col] = col_map[c]
            continue
            
        # 2. Match after replacing underscore
        if c_space in col_map:
            rename[original_col] = col_map[c_space]
            continue
            
        # 3. Fuzzy Heuristic Substring Match for critical columns
        if "sku" in c:
            rename[original_col] = "sku"
        elif "qty" in c or "quantity" in c:
            rename[original_col] = "quantity"
        elif "price" in c and ("sell" in c or "selling" in c):
            rename[original_col] = "selling_price"
        elif "price" in c and "cost" in c:
            rename[original_col] = "cost_price"
        elif "mrp" in c:
            rename[original_col] = "mrp"
        elif "market" in c or "platform" in c or "channel" in c:
            rename[original_col] = "marketplace"
        elif "order" in c and "id" in c:
            rename[original_col] = "external_order_id"
        elif "stock" in c and "avail" in c:
            rename[original_col] = "available_stock"
        elif "stock" in c and "reserv" in c:
            rename[original_col] = "reserved_stock"
        elif "stock" in c:
            rename[original_col] = "available_stock" # fallback
        elif "spend" in c and "ad" in c:
            rename[original_col] = "ad_spend"
        elif "return" in c and "ad" in c:
            rename[original_col] = "revenue_from_ads"
            
    return df.rename(columns=rename)


from datetime import date, datetime, timedelta

def _parse_date(val) -> Optional[date]:
    if pd.isna(val):
        return None
    if isinstance(val, (date, datetime)):
        return val if isinstance(val, date) else val.date()
    
    # Handle Excel serial dates (floats)
    try:
        if isinstance(val, (int, float)) or (isinstance(val, str) and val.replace('.','',1).isdigit()):
            float_val = float(val)
            # Excel dates are days since Dec 30, 1899
            return (datetime(1899, 12, 30) + timedelta(days=float_val)).date()
    except Exception:
        pass

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


async def _resolve_products_batch(db: AsyncSession, seller_id: str, skus: list[str], marketplaces: list[str], product_cache: dict):
    """
    Efficiently resolves a list of (sku, marketplace) pairs to product_ids in batches.
    """
    # Filter out what's already in cache
    missing_keys = []
    seen_keys = set()
    for s, m in zip(skus, marketplaces):
        key = (s, m)
        if key not in product_cache and key not in seen_keys:
            missing_keys.append(key)
            seen_keys.add(key)
    
    if not missing_keys:
        return

    # Step 1: Query existing products
    # We use a tuple-based IN clause for (sku, marketplace)
    from sqlalchemy import tuple_
    result = await db.execute(
        select(Product.product_id, Product.sku, Product.marketplace).where(
            Product.seller_id == seller_id,
            tuple_(Product.sku, Product.marketplace).in_(missing_keys)
        )
    )
    
    found_keys = set()
    for row in result:
        key = (row.sku, row.marketplace)
        product_cache[key] = str(row.product_id)
        found_keys.add(key)
    
    # Step 2: Bulk-insert missing products
    really_missing = [k for k in missing_keys if k not in found_keys]
    if really_missing:
        new_products = [
            Product(
                seller_id=seller_id,
                sku=sku,
                product_name=sku,
                marketplace=m,
                is_active=True
            ) for sku, m in really_missing
        ]
        db.add_all(new_products)
        await db.flush()
        
        for p in new_products:
            product_cache[(p.sku, p.marketplace)] = str(p.product_id)

async def _resolve_product(db: AsyncSession, seller_id: str, sku: str, marketplace: str, product_cache: dict) -> Optional[str]:
    """Single resolve fallback (uses batch logic internally)."""
    cache_key = (sku, marketplace)
    if cache_key in product_cache:
        return product_cache[cache_key]
    
    await _resolve_products_batch(db, seller_id, [sku], [marketplace], product_cache)
    return product_cache.get(cache_key)


# ── Domain Parsers ──────────────────────────────────────────────

async def ingest_orders(db: AsyncSession, df: pd.DataFrame, seller_id: str, snapshot_date: date) -> dict:
    df = _normalise_columns(df, ORDER_COL_MAP)

    rows_inserted = 0
    rows_skipped  = 0
    product_cache = {}
    
    orders_to_add = []
    
    # Pre-warm product cache in one batch
    skus = df.get("sku", pd.Series(dtype=str)).astype(str).str.strip().tolist()
    marketplaces = df.get("marketplace", pd.Series(dtype=str)).astype(str).str.strip().tolist()
    await _resolve_products_batch(db, seller_id, skus, marketplaces, product_cache)

    # Use itertuples for massive speedup over iterrows
    for row in df.itertuples(index=False):
        row_dict = row._asdict()
        try:
            sku         = str(row_dict.get("sku", "")).strip()
            if not sku or sku == "nan":
                # Fallback if SKU column is entirely missing in large test datasets
                sku = "UNKNOWN-SKU"
                
            marketplace = str(row_dict.get("marketplace", "unknown")).strip()

            product_id = await _resolve_product(db, seller_id, sku, marketplace, product_cache)

            order = Order(
                external_order_id   = str(row_dict.get("external_order_id", "")) or None,
                seller_id           = seller_id,
                product_id          = product_id,
                marketplace         = marketplace,
                order_status        = str(row_dict.get("order_status", "unknown")),
                quantity            = _safe_int(row_dict.get("quantity"), 1),
                selling_price       = _safe_float(row_dict.get("selling_price")),
                discount            = _safe_float(row_dict.get("discount")),
                tax                 = _safe_float(row_dict.get("tax")),
                shipping_fee        = _safe_float(row_dict.get("shipping_fee")),
                order_date          = _parse_date(row_dict.get("order_date")) or snapshot_date,
                delivery_date       = _parse_date(row_dict.get("delivery_date")),
                return_flag         = bool(row_dict.get("return_flag", False)),
                cancellation_reason = str(row_dict.get("cancellation_reason", "")) or None,
                snapshot_date       = snapshot_date,
            )
            orders_to_add.append(order)
            rows_inserted += 1
        except Exception as e:
            rows_skipped += 1

    if orders_to_add:
        db.add_all(orders_to_add)
    await db.commit()
    return {"inserted": rows_inserted, "skipped": rows_skipped, "domain": "orders"}


async def ingest_inventory(db: AsyncSession, df: pd.DataFrame, seller_id: str, snapshot_date: date) -> dict:
    df = _normalise_columns(df, INVENTORY_COL_MAP)

    rows_inserted = 0
    rows_skipped  = 0
    product_cache = {}
    
    # Pre-warm product cache in one batch
    skus = df.get("sku", pd.Series(dtype=str)).astype(str).str.strip().tolist()
    marketplaces = df.get("marketplace", pd.Series(dtype=str)).astype(str).str.strip().tolist()
    await _resolve_products_batch(db, seller_id, skus, marketplaces, product_cache)

    values_list = []

    # Use itertuples for massive speedup
    for row in df.itertuples(index=False):
        row_dict = row._asdict()
        try:
            sku         = str(row_dict.get("sku", "")).strip()
            if not sku or sku == "nan":
                sku = "UNKNOWN-SKU"
                
            marketplace = str(row_dict.get("marketplace", "unknown")).strip()

            product_id = await _resolve_product(db, seller_id, sku, marketplace, product_cache)
            snap_date  = _parse_date(row_dict.get("snapshot_date")) or snapshot_date

            values_list.append({
                "seller_id":         seller_id,
                "product_id":        product_id,
                "marketplace":       marketplace,
                "available_stock":   _safe_int(row_dict.get("available_stock")),
                "reserved_stock":    _safe_int(row_dict.get("reserved_stock")),
                "reorder_threshold": _safe_int(row_dict.get("reorder_threshold"), 10),
                "days_of_stock":     _safe_float(row_dict.get("days_of_stock")) or None,
                "warehouse_location": str(row_dict.get("warehouse_location", "")) or None,
                "snapshot_date":     snap_date,
            })
            rows_inserted += 1
        except Exception:
            rows_skipped += 1

    if values_list:
        stmt = pg_insert(InventorySnapshot).values(values_list).on_conflict_do_update(
            index_elements=["seller_id", "product_id", "marketplace", "snapshot_date"],
            set_={
                "available_stock": pg_insert(InventorySnapshot).excluded.available_stock,
                "reserved_stock": pg_insert(InventorySnapshot).excluded.reserved_stock,
            },
        )
        await db.execute(stmt)

    await db.commit()
    return {"inserted": rows_inserted, "skipped": rows_skipped, "domain": "inventory"}


async def ingest_pricing(db: AsyncSession, df: pd.DataFrame, seller_id: str, snapshot_date: date) -> dict:
    df = _normalise_columns(df, PRICING_COL_MAP)

    rows_inserted = 0
    rows_skipped  = 0
    product_cache = {}
    
    # Pre-warm product cache in one batch
    skus = df.get("sku", pd.Series(dtype=str)).astype(str).str.strip().tolist()
    marketplaces = df.get("marketplace", pd.Series(dtype=str)).astype(str).str.strip().tolist()
    await _resolve_products_batch(db, seller_id, skus, marketplaces, product_cache)

    values_list = []

    for row in df.itertuples(index=False):
        row_dict = row._asdict()
        try:
            sku         = str(row_dict.get("sku", "")).strip()
            if not sku or sku == "nan":
                sku = "UNKNOWN-SKU"
                
            marketplace = str(row_dict.get("marketplace", "unknown")).strip()

            product_id  = await _resolve_product(db, seller_id, sku, marketplace, product_cache)
            snap_date   = _parse_date(row_dict.get("snapshot_date")) or snapshot_date
            sell_price  = _safe_float(row_dict.get("selling_price"))
            cost_price  = _safe_float(row_dict.get("cost_price")) or None
            comm_amount = _safe_float(row_dict.get("commission_amount"))

            values_list.append({
                "seller_id":           seller_id,
                "product_id":          product_id,
                "marketplace":         marketplace,
                "selling_price":       sell_price,
                "cost_price":          cost_price,
                "mrp":                 _safe_float(row_dict.get("mrp")) or None,
                "commission_pct":      _safe_float(row_dict.get("commission_pct")),
                "commission_amount":   comm_amount,
                "discount_percentage": _safe_float(row_dict.get("discount_percentage")),
                "snapshot_date":       snap_date,
            })
            rows_inserted += 1
        except Exception:
            rows_skipped += 1

    if values_list:
        stmt = pg_insert(PricingSnapshot).values(values_list).on_conflict_do_update(
            index_elements=["seller_id", "product_id", "marketplace", "snapshot_date"],
            set_={
                "selling_price": pg_insert(PricingSnapshot).excluded.selling_price,
                "cost_price": pg_insert(PricingSnapshot).excluded.cost_price
            },
        )
        await db.execute(stmt)

    await db.commit()
    return {"inserted": rows_inserted, "skipped": rows_skipped, "domain": "pricing"}


async def ingest_traffic(db: AsyncSession, df: pd.DataFrame, seller_id: str, snapshot_date: date) -> dict:
    df = _normalise_columns(df, TRAFFIC_COL_MAP)

    rows_inserted = 0
    rows_skipped  = 0
    product_cache = {}
    
    # Pre-warm product cache in one batch
    skus = df.get("sku", pd.Series(dtype=str)).astype(str).str.strip().tolist()
    marketplaces = df.get("marketplace", pd.Series(dtype=str)).astype(str).str.strip().tolist()
    await _resolve_products_batch(db, seller_id, skus, marketplaces, product_cache)

    values_list = []

    for row in df.itertuples(index=False):
        row_dict = row._asdict()
        try:
            sku         = str(row_dict.get("sku", "")).strip()
            if not sku or sku == "nan":
                sku = "UNKNOWN-SKU"
                
            marketplace = str(row_dict.get("marketplace", "unknown")).strip()

            product_id  = await _resolve_product(db, seller_id, sku, marketplace, product_cache)
            metric_date = _parse_date(row_dict.get("metric_date")) or snapshot_date

            values_list.append({
                "seller_id":        seller_id,
                "product_id":       product_id,
                "marketplace":      marketplace,
                "metric_date":      metric_date,
                "impressions":      _safe_int(row_dict.get("impressions")),
                "clicks":           _safe_int(row_dict.get("clicks")),
                "sessions":         _safe_int(row_dict.get("sessions")),
                "page_views":       _safe_int(row_dict.get("page_views")),
                "orders":           _safe_int(row_dict.get("orders")),
                "ad_spend":         _safe_float(row_dict.get("ad_spend")),
                "revenue_from_ads": _safe_float(row_dict.get("revenue_from_ads")),
            })
            rows_inserted += 1
        except Exception:
            rows_skipped += 1

    if values_list:
        stmt = pg_insert(TrafficMetric).values(values_list).on_conflict_do_update(
            index_elements=["seller_id", "product_id", "marketplace", "metric_date"],
            set_={
                "impressions": pg_insert(TrafficMetric).excluded.impressions,
                "clicks": pg_insert(TrafficMetric).excluded.clicks,
                "ad_spend": pg_insert(TrafficMetric).excluded.ad_spend,
            },
        )
        await db.execute(stmt)

    await db.commit()
    return {"inserted": rows_inserted, "skipped": rows_skipped, "domain": "traffic"}


async def ingest_logistics(db: AsyncSession, df: pd.DataFrame, seller_id: str, snapshot_date: date) -> dict:
    df = _normalise_columns(df, LOGISTICS_COL_MAP)

    rows_inserted = 0
    rows_skipped  = 0
    
    logistics_to_add = []

    for row in df.itertuples(index=False):
        row_dict = row._asdict()
        try:
            marketplace = str(row_dict.get("marketplace", "unknown")).strip()
            ext_order_id = str(row_dict.get("external_order_id", "")).strip() or None

            logic_row = LogisticsMetric(
                seller_id          = seller_id,
                marketplace        = marketplace,
                courier_name       = str(row_dict.get("courier_name", "")) or None,
                tracking_id        = str(row_dict.get("tracking_id", "")) or None,
                fulfillment_type   = str(row_dict.get("fulfillment_type", "seller")),
                warehouse_id       = str(row_dict.get("warehouse_id", "")) or None,
                dispatch_date      = _parse_date(row_dict.get("dispatch_date")),
                expected_delivery  = _parse_date(row_dict.get("expected_delivery")),
                actual_delivery    = _parse_date(row_dict.get("actual_delivery")),
                delivery_status    = str(row_dict.get("delivery_status", "unknown")),
                rto_flag           = bool(row_dict.get("rto_flag", False)),
                rto_reason         = str(row_dict.get("rto_reason", "")) or None,
                snapshot_date      = _parse_date(row_dict.get("snapshot_date")) or snapshot_date,
            )
            logistics_to_add.append(logic_row)
            rows_inserted += 1
        except Exception:
            rows_skipped += 1

    if logistics_to_add:
        db.add_all(logistics_to_add)
    await db.commit()
    return {"inserted": rows_inserted, "skipped": rows_skipped, "domain": "logistics"}
