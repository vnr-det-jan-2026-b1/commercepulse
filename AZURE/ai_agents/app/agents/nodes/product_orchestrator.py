import os
import json
from typing import Dict, Any
from app.agents.state import SystemState

def run_product_orchestrator(state: SystemState) -> dict:
    """
    Orchestrator node for Per-Product Analysis.
    Takes the product_data provided in the state and enhances it with pgvector context.
    """
    from app.db.supabase_client import get_supabase_client
    
    seller_id = state.get("seller_id")
    product_id = state.get("product_id")
    raw_snapshot = state.get("snapshot_data", {})
    
    print(f"🧠 [Product Orchestrator] Gathering data for product {product_id}...")
    
    # 1. Structure the raw snapshot into proper business intelligence sections
    enriched_snapshot = {
        "product_identity": {
            "product_name": raw_snapshot.get("product_name"),
            "sku": raw_snapshot.get("sku"),
            "category": raw_snapshot.get("category"),
            "sub_category": raw_snapshot.get("sub_category"),
            "brand": raw_snapshot.get("brand"),
            "primary_marketplace": raw_snapshot.get("marketplace"),
        },
        "profit_and_loss": {
            "total_revenue": raw_snapshot.get("total_revenue", 0),
            "total_orders": raw_snapshot.get("total_orders", 0),
            "avg_order_value": raw_snapshot.get("avg_order_value", 0),
            "discounted_orders": raw_snapshot.get("discounted_orders", 0),
            "total_discount_given": raw_snapshot.get("total_discount_given", 0),
            "total_shipping_collected": raw_snapshot.get("total_shipping_collected", 0),
            "total_returns": raw_snapshot.get("total_returns", 0),
            "return_rate_pct": raw_snapshot.get("return_rate_pct", 0),
        },
        "pricing_by_marketplace": raw_snapshot.get("pricing_by_marketplace", []),
        "revenue_by_marketplace": raw_snapshot.get("revenue_by_marketplace", []),
        "advertising_performance": {
            "total_ad_spend": raw_snapshot.get("total_ad_spend", 0),
            "total_ad_revenue": raw_snapshot.get("total_ad_revenue", 0),
            "roas": raw_snapshot.get("roas", 0),
            "total_impressions": raw_snapshot.get("total_impressions", 0),
            "total_clicks": raw_snapshot.get("total_clicks", 0),
            "ctr_pct": raw_snapshot.get("ctr_pct", 0),
            "cost_per_click": raw_snapshot.get("cost_per_click", 0),
        },
        "inventory_health": {
            "stock_level": raw_snapshot.get("stock_level", 0),
            "reserved_stock": raw_snapshot.get("reserved_stock", 0),
            "reorder_threshold": raw_snapshot.get("reorder_threshold", 0),
            "days_of_stock": raw_snapshot.get("days_of_stock", 0),
        },
        "logistics_quality": {
            "rto_count": raw_snapshot.get("rto_count", 0),
            "rto_rate_pct": raw_snapshot.get("rto_rate_pct", 0),
            "avg_delivery_days": raw_snapshot.get("avg_delivery_days", 0),
        },
        "historical_context": ""
    }
    
    # 2. Add pgvector historical context (if available)
    try:
        supabase = get_supabase_client()
        # Find past analyses for this product
        response = supabase.table("product_embeddings") \
            .select("summary_text, metadata, embed_date") \
            .eq("seller_id", seller_id) \
            .eq("product_id", product_id) \
            .order("embed_date", desc=True) \
            .limit(3) \
            .execute()
            
        if response.data:
            context_items = [f"[{item['embed_date']}] {item['summary_text']}" for item in response.data]
            enriched_snapshot["historical_context"] = "\n".join(context_items)
            print(f"  └─ Found {len(context_items)} historical embeddings for context.")
    except Exception as e:
        print(f"  └─ Warning: Could not fetch pgvector context: {e}")
        
    return {"snapshot_data": enriched_snapshot}
