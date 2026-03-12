"""
Column alias maps for batch ingestion pipeline.
Maps flexible Excel column names → canonical BigQuery column names.
Ported directly from AZURE/backend/app/services/ingestion.py
"""

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

# Domain → (col_map, required_fields, date_fields, bool_fields)
DOMAIN_CONFIG = {
    "orders": (
        ORDER_COL_MAP,
        ["sku", "marketplace", "selling_price", "order_date"],
        ["order_date", "delivery_date"],
        ["return_flag"],
    ),
    "inventory": (
        INVENTORY_COL_MAP,
        ["sku", "marketplace"],
        ["snapshot_date"],
        [],
    ),
    "pricing": (
        PRICING_COL_MAP,
        ["sku", "marketplace", "selling_price"],
        ["snapshot_date"],
        [],
    ),
    "traffic": (
        TRAFFIC_COL_MAP,
        ["sku", "marketplace", "metric_date"],
        ["metric_date"],
        [],
    ),
    "logistics": (
        LOGISTICS_COL_MAP,
        ["marketplace", "delivery_status"],
        ["dispatch_date", "expected_delivery", "actual_delivery", "snapshot_date"],
        ["rto_flag"],
    ),
}
