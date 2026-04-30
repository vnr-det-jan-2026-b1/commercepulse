import pandas as pd
import numpy as np
from datetime import date, timedelta
import random

def create_test_dataset():
    print("Generating test dataset...")
    
    # Common Product SKUs
    skus = [f"SKU-{i:04d}" for i in range(1, 21)]
    product_names = [f"Product {i}" for i in range(1, 21)]
    categories = ["Electronics", "Apparel", "Home", "Beauty"]
    marketplaces = ["Amazon", "Shopify", "Walmart"]
    
    # 1. Orders
    num_orders = 500
    orders_data = {
        "order_id": [f"ORD-{i:05d}" for i in range(1, num_orders + 1)],
        "marketplace": np.random.choice(marketplaces, num_orders),
        "order_date": [date.today() - timedelta(days=random.randint(0, 30)) for _ in range(num_orders)],
        "sku": np.random.choice(skus, num_orders),
        "quantity": np.random.randint(1, 5, num_orders),
        "selling_price": np.random.uniform(10, 200, num_orders).round(2),
        "discount": np.random.choice([0, 5, 10, 20], num_orders),
        "tax": np.random.uniform(1, 15, num_orders).round(2),
        "shipping_fee": np.random.choice([0, 4.99, 9.99], num_orders),
        "order_status": np.random.choice(["delivered", "shipped", "cancelled", "processing"], num_orders, p=[0.7, 0.15, 0.05, 0.1]),
        "return_flag": np.random.choice([True, False], num_orders, p=[0.05, 0.95]),
        "customer_city": np.random.choice(["New York", "Los Angeles", "Chicago", "Houston", "Miami"], num_orders),
        "customer_state": np.random.choice(["NY", "CA", "IL", "TX", "FL"], num_orders),
    }
    df_orders = pd.DataFrame(orders_data)

    # 2. Inventory
    inventory_data = []
    for sku in skus:
        for mkp in marketplaces:
            inventory_data.append({
                "sku": sku,
                "marketplace": mkp,
                "available_stock": random.randint(0, 200),
                "reserved_stock": random.randint(0, 20),
                "reorder_threshold": random.randint(10, 50),
                "warehouse_location": random.choice(["WH-1", "WH-2", "WH-3"])
            })
    df_inventory = pd.DataFrame(inventory_data)

    # 3. Pricing
    pricing_data = []
    for sku in skus:
        cost = round(random.uniform(5, 50), 2)
        for mkp in marketplaces:
            selling = round(cost * random.uniform(1.5, 3.0), 2)
            pricing_data.append({
                "sku": sku,
                "marketplace": mkp,
                "cost_price": cost,
                "mrp": round(selling * 1.2, 2),
                "selling_price": selling,
                "commission_pct": random.choice([8, 10, 15]),
                "discount_percentage": random.choice([0, 5, 10])
            })
    df_pricing = pd.DataFrame(pricing_data)

    # 4. Traffic
    traffic_data = []
    for _ in range(200):
        traffic_data.append({
            "metric_date": date.today() - timedelta(days=random.randint(0, 30)),
            "marketplace": random.choice(marketplaces),
            "sku": random.choice(skus),
            "impressions": random.randint(100, 5000),
            "clicks": random.randint(10, 500),
            "sessions": random.randint(5, 300),
            "orders": random.randint(0, 50),
            "ad_spend": round(random.uniform(5, 100), 2),
            "revenue_from_ads": round(random.uniform(10, 500), 2)
        })
    df_traffic = pd.DataFrame(traffic_data)

    # 5. Logistics
    logistics_count = 300
    logistics_data = {
        "shipment_id": [f"SHP-{i:05d}" for i in range(1, logistics_count + 1)],
        "order_id": np.random.choice(df_orders["order_id"], logistics_count),
        "marketplace": np.random.choice(marketplaces, logistics_count),
        "carrier": np.random.choice(["FedEx", "UPS", "USPS", "DHL"], logistics_count),
        "dispatch_date": [date.today() - timedelta(days=random.randint(5, 30)) for _ in range(logistics_count)],
        "estimated_delivery": [date.today() - timedelta(days=random.randint(2, 25)) for _ in range(logistics_count)],
        "actual_delivery": [date.today() - timedelta(days=random.randint(0, 24)) for _ in range(logistics_count)],
        "delivery_status": np.random.choice(["delivered", "in_transit", "delayed"], logistics_count, p=[0.8, 0.15, 0.05]),
        "rto_flag": np.random.choice([True, False], logistics_count, p=[0.02, 0.98]),
        "shipping_cost": np.random.uniform(3, 15, logistics_count).round(2),
        "fulfillment_type": np.random.choice(["FBA", "FBM", "WFS"], logistics_count)
    }
    df_logistics = pd.DataFrame(logistics_data)

    # Products reference (not typically a separate sheet in the upload but required by DB implicitly, 
    # though ingestion scripts usually upsert products from the sheets directly based on SKU)
    # The ingestion script expects: sku, product_name, category in various sheets, so let's add them to Inventory and Orders
    df_inventory["product_name"] = df_inventory["sku"].apply(lambda s: product_names[int(s.split('-')[1])-1])
    df_inventory["category"] = df_inventory["sku"].apply(lambda s: categories[int(s.split('-')[1]) % len(categories)])

    # Write to Excel
    filepath = "test_dataset.xlsx"
    with pd.ExcelWriter(filepath, engine="openpyxl") as writer:
        df_orders.to_excel(writer, sheet_name="Orders", index=False)
        df_inventory.to_excel(writer, sheet_name="Inventory", index=False)
        df_pricing.to_excel(writer, sheet_name="Pricing", index=False)
        df_traffic.to_excel(writer, sheet_name="Traffic", index=False)
        df_logistics.to_excel(writer, sheet_name="Logistics", index=False)

    print(f"✅ Successfully generated {filepath}")

if __name__ == "__main__":
    create_test_dataset()
